import { animate } from 'motion';
import JSZip from 'jszip';
import confetti from 'canvas-confetti';

// ============================================================================
// State Management
// ============================================================================
const state = {
  templateImage: null,
  templateWidth: 0,
  templateHeight: 0,
  normalizedPos: { x: 0.5, y: 0.5 }, // 0.0 to 1.0 relative to canvas
  fontFamily: 'America',
  fontSize: 56,
  textColor: '#111827',
  textAlign: 'center',
  recipientNames: [],
  isDragging: false,
  isGenerating: false,
  lastGeneratedBlob: null
};

// ============================================================================
// DOM Element References
// ============================================================================
const elements = {
  templateInput: document.getElementById('template-input'),
  templateDropzone: document.getElementById('template-dropzone'),
  templatePreviewBar: document.getElementById('template-preview-bar'),
  previewFilename: document.getElementById('preview-filename'),
  previewDim: document.getElementById('preview-dim'),
  btnChangeTemplate: document.getElementById('btn-change-template'),

  fontSelect: document.getElementById('font-family-select'),
  customFontInput: document.getElementById('custom-font-input'),
  fontSizeSlider: document.getElementById('font-size-slider'),
  fontSizeVal: document.getElementById('font-size-val'),
  textColorPicker: document.getElementById('text-color-picker'),
  alignControl: document.getElementById('align-control'),

  namesInput: document.getElementById('names-input'),
  namesCount: document.getElementById('names-count'),
  btnSampleNames: document.getElementById('btn-sample-names'),

  btnGenerate: document.getElementById('btn-generate'),
  btnGenerateLabel: document.getElementById('btn-generate-label'),
  progressWrap: document.getElementById('progress-wrap'),
  progressStatus: document.getElementById('progress-status'),
  progressPercent: document.getElementById('progress-percent'),
  progressBar: document.getElementById('progress-bar'),
  downloadBanner: document.getElementById('download-banner'),
  downloadCountText: document.getElementById('download-count-text'),
  btnDownloadAgain: document.getElementById('btn-download-again'),

  coordsDisplay: document.getElementById('coords-display'),
  stageViewport: document.getElementById('stage-viewport'),
  stageEmptyState: document.getElementById('stage-empty-state'),
  canvasContainer: document.getElementById('canvas-container'),
  stageCanvas: document.getElementById('stage-canvas'),
  draggableMarker: document.getElementById('draggable-marker'),
  markerPreviewText: document.getElementById('marker-preview-text')
};

const ctx = elements.stageCanvas.getContext('2d');

// Sample names list for quick testing
const SAMPLE_NAMES = [
  "Alexander Wright",
  "Sophia Martinez",
  "Liam O'Connor",
  "Emma Watson",
  "Ethan Takahashi",
  "Olivia Patel",
  "Lucas Silva",
  "Isabella Rossi",
  "Noah Zimmerman",
  "Ava Chen"
];

// ============================================================================
// Initialization & Event Listeners
// ============================================================================
function init() {
  setupTemplateUpload();
  setupStyleControls();
  setupNamesInput();
  setupDragInteraction();
  setupBatchGeneration();
  setupSampleDemoTrigger();

  // Load America font eagerly
  document.fonts.load(`56px 'America'`).catch(() => {});
}

// ============================================================================
// Step 1: Template Upload & Canvas Sizing
// ============================================================================
function setupTemplateUpload() {
  const { templateInput, templateDropzone, btnChangeTemplate } = elements;

  templateDropzone.addEventListener('click', (e) => {
    if (e.target !== btnChangeTemplate && !btnChangeTemplate.contains(e.target)) {
      templateInput.click();
    }
  });

  templateInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      loadTemplateFile(e.target.files[0]);
    }
  });

  // Drag and Drop with Motion feedback
  templateDropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    templateDropzone.classList.add('dragover');
    animate(templateDropzone, { scale: 1.02 }, { type: "spring", bounce: 0.3 });
  });

  templateDropzone.addEventListener('dragleave', () => {
    templateDropzone.classList.remove('dragover');
    animate(templateDropzone, { scale: 1.0 }, { type: "spring", bounce: 0.2 });
  });

  templateDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    templateDropzone.classList.remove('dragover');
    animate(templateDropzone, { scale: 1.0 }, { type: "spring", bounce: 0.3 });
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      loadTemplateFile(e.dataTransfer.files[0]);
    }
  });

  btnChangeTemplate.addEventListener('click', (e) => {
    e.stopPropagation();
    templateInput.value = '';
    templateInput.click();
  });
}

function loadTemplateFile(file) {
  const reader = new FileReader();
  reader.onload = (event) => {
    const img = new Image();
    img.onload = () => {
      setTemplateImage(img, file.name);
    };
    img.src = event.target.result;
  };
  reader.readAsDataURL(file);
}

function setTemplateImage(img, filename = "certificate-template.png") {
  state.templateImage = img;
  state.templateWidth = img.naturalWidth || img.width;
  state.templateHeight = img.naturalHeight || img.height;

  elements.previewFilename.textContent = filename;
  elements.previewDim.textContent = `${state.templateWidth} × ${state.templateHeight} px`;

  elements.templateDropzone.querySelector('.dropzone-content').classList.add('visually-hidden');
  elements.templatePreviewBar.classList.remove('visually-hidden');

  // Reveal canvas container with spring animation
  elements.stageEmptyState.classList.add('visually-hidden');
  elements.canvasContainer.classList.remove('visually-hidden');

  elements.stageCanvas.width = state.templateWidth;
  elements.stageCanvas.height = state.templateHeight;

  animate(elements.canvasContainer, { opacity: [0, 1], scale: [0.95, 1] }, { type: "spring", bounce: 0.2, visualDuration: 0.35 });

  updateMarkerPosition();
  renderPreview();
}

// ============================================================================
// Step 2: Typography & Styling Controls
// ============================================================================
function setupStyleControls() {
  const { fontSelect, customFontInput, fontSizeSlider, fontSizeVal, textColorPicker, alignControl } = elements;

  // Font family select
  fontSelect.addEventListener('change', (e) => {
    if (e.target.value === 'CUSTOM') {
      customFontInput.click();
    } else {
      state.fontFamily = e.target.value;
      renderPreview();
    }
  });

  // Custom font file upload
  customFontInput.addEventListener('change', async (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const fontName = `UserFont_${Date.now()}`;
      try {
        const buffer = await file.arrayBuffer();
        const fontFace = new FontFace(fontName, buffer);
        await fontFace.load();
        document.fonts.add(fontFace);

        // Add custom option to dropdown
        const opt = document.createElement('option');
        opt.value = fontName;
        opt.textContent = `Custom: ${file.name}`;
        opt.selected = true;
        fontSelect.insertBefore(opt, fontSelect.lastElementChild);

        state.fontFamily = fontName;
        renderPreview();
      } catch (err) {
        alert("Could not load font file: " + err.message);
        fontSelect.value = 'America';
      }
    } else {
      fontSelect.value = state.fontFamily;
    }
  });

  // Font size slider
  fontSizeSlider.addEventListener('input', (e) => {
    const size = parseInt(e.target.value, 10);
    state.fontSize = size;
    fontSizeVal.textContent = `${size}px`;
    renderPreview();
  });

  // Text color picker
  textColorPicker.addEventListener('input', (e) => {
    state.textColor = e.target.value;
    renderPreview();
  });

  // Alignment segmented control
  alignControl.querySelectorAll('.segment-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      alignControl.querySelectorAll('.segment-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.textAlign = btn.getAttribute('data-align');
      renderPreview();
    });
  });
}

function getCanvasTextAlign(align) {
  // In Canvas 2D API:
  // - ctx.textAlign = 'right' places text to the LEFT of the anchor (x)
  // - ctx.textAlign = 'left' places text to the RIGHT of the anchor (x)
  // Mapping 'left' -> 'right' and 'right' -> 'left' ensures that clicking
  // 'Left' aligns text to the left of the position, and 'Right' aligns to the right.
  if (align === 'left') return 'right';
  if (align === 'right') return 'left';
  return 'center';
}


// ============================================================================
// Step 3: Recipient Names Input
// ============================================================================
function setupNamesInput() {
  const { namesInput, namesCount, btnSampleNames, markerPreviewText } = elements;

  namesInput.addEventListener('input', () => {
    const lines = namesInput.value.split('\n').map((l) => l.trim()).filter(Boolean);
    state.recipientNames = lines;
    namesCount.textContent = `${lines.length} recipient${lines.length === 1 ? '' : 's'}`;

    const previewName = lines[0] || 'Recipient Name';
    markerPreviewText.textContent = previewName;
    renderPreview();
  });

  btnSampleNames.addEventListener('click', () => {
    namesInput.value = SAMPLE_NAMES.join('\n');
    namesInput.dispatchEvent(new Event('input'));
    animate(btnSampleNames, { scale: [1.15, 1] }, { type: "spring", bounce: 0.4 });
  });
}

// ============================================================================
// Interactive Drag & Click Placement Engine
// ============================================================================
function setupDragInteraction() {
  const { canvasContainer, draggableMarker, stageCanvas } = elements;

  // Click on canvas to instantly position marker
  canvasContainer.addEventListener('pointerdown', (e) => {
    if (e.target === draggableMarker || draggableMarker.contains(e.target)) return;
    
    const rect = canvasContainer.getBoundingClientRect();
    const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    const y = Math.max(0, Math.min(rect.height, e.clientY - rect.top));

    state.normalizedPos.x = x / rect.width;
    state.normalizedPos.y = y / rect.height;

    updateMarkerPosition();
    renderPreview();

    animate(draggableMarker, { scale: [1.3, 1] }, { type: "spring", bounce: 0.4, visualDuration: 0.3 });
  });

  // Dragging the marker
  let startX = 0, startY = 0;
  let startNormX = 0, startNormY = 0;

  draggableMarker.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    state.isDragging = true;
    draggableMarker.setPointerCapture(e.pointerId);

    startX = e.clientX;
    startY = e.clientY;
    startNormX = state.normalizedPos.x;
    startNormY = state.normalizedPos.y;

    animate(draggableMarker, { scale: 1.1 }, { type: "spring", bounce: 0.2 });
  });

  draggableMarker.addEventListener('pointermove', (e) => {
    if (!state.isDragging) return;
    const rect = canvasContainer.getBoundingClientRect();

    const dx = e.clientX - startX;
    const dy = e.clientY - startY;

    const newX = Math.max(0, Math.min(rect.width, (startNormX * rect.width) + dx));
    const newY = Math.max(0, Math.min(rect.height, (startNormY * rect.height) + dy));

    state.normalizedPos.x = newX / rect.width;
    state.normalizedPos.y = newY / rect.height;

    updateMarkerPosition();
    renderPreview();
  });

  function stopDrag(e) {
    if (state.isDragging) {
      state.isDragging = false;
      try { draggableMarker.releasePointerCapture(e.pointerId); } catch (_) {}
      animate(draggableMarker, { scale: 1.0 }, { type: "spring", bounce: 0.35, visualDuration: 0.3 });
    }
  }

  draggableMarker.addEventListener('pointerup', stopDrag);
  draggableMarker.addEventListener('pointercancel', stopDrag);
}

function updateMarkerPosition() {
  const { draggableMarker, coordsDisplay } = elements;
  const leftPercent = (state.normalizedPos.x * 100).toFixed(2);
  const topPercent = (state.normalizedPos.y * 100).toFixed(2);

  draggableMarker.style.left = `${leftPercent}%`;
  draggableMarker.style.top = `${topPercent}%`;

  const realX = Math.round(state.normalizedPos.x * state.templateWidth);
  const realY = Math.round(state.normalizedPos.y * state.templateHeight);
  coordsDisplay.textContent = `X: ${realX}, Y: ${realY}`;
}

// ============================================================================
// Canvas Real-Time Rendering
// ============================================================================
function renderPreview() {
  if (!state.templateImage) return;

  // 1. Draw base certificate image
  ctx.clearRect(0, 0, state.templateWidth, state.templateHeight);
  ctx.drawImage(state.templateImage, 0, 0, state.templateWidth, state.templateHeight);

  // 2. Compute coordinates in full resolution
  const x = state.normalizedPos.x * state.templateWidth;
  const y = state.normalizedPos.y * state.templateHeight;

  // 3. Render sample text
  const previewName = state.recipientNames[0] || 'Sample Recipient Name';

  ctx.save();
  ctx.font = `${state.fontSize}px ${state.fontFamily}`;
  ctx.fillStyle = state.textColor;
  ctx.textAlign = getCanvasTextAlign(state.textAlign);
  ctx.textBaseline = 'middle';

  ctx.fillText(previewName, x, y);
  ctx.restore();

  // Keep marker tag visually aligned with the text alignment
  const handle = elements.draggableMarker.querySelector('.marker-handle');
  if (handle) {
    if (state.textAlign === 'left') {
      handle.style.alignItems = 'flex-end';
    } else if (state.textAlign === 'right') {
      handle.style.alignItems = 'flex-start';
    } else {
      handle.style.alignItems = 'center';
    }
  }
}

// ============================================================================
// Step 4: Batch Certificate Generation & Export
// ============================================================================
function setupBatchGeneration() {
  const { btnGenerate, btnGenerateLabel, progressWrap, progressStatus, progressPercent, progressBar, downloadBanner, downloadCountText, btnDownloadAgain } = elements;

  btnGenerate.addEventListener('click', async () => {
    if (state.isGenerating) return;

    if (!state.templateImage) {
      alert("Please upload a certificate template first.");
      return;
    }

    if (!state.recipientNames || state.recipientNames.length === 0) {
      alert("Please enter at least one recipient name.");
      elements.namesInput.focus();
      return;
    }

    state.isGenerating = true;
    btnGenerate.disabled = true;
    btnGenerateLabel.textContent = "Processing batch...";

    progressWrap.classList.remove('visually-hidden');
    downloadBanner.classList.add('visually-hidden');

    const total = state.recipientNames.length;
    const zip = new JSZip();

    // Offscreen high-resolution rendering canvas
    const offscreen = document.createElement('canvas');
    offscreen.width = state.templateWidth;
    offscreen.height = state.templateHeight;
    const offCtx = offscreen.getContext('2d');

    const posX = state.normalizedPos.x * state.templateWidth;
    const posY = state.normalizedPos.y * state.templateHeight;

    for (let i = 0; i < total; i++) {
      const name = state.recipientNames[i];

      // Draw base template
      offCtx.clearRect(0, 0, state.templateWidth, state.templateHeight);
      offCtx.drawImage(state.templateImage, 0, 0, state.templateWidth, state.templateHeight);

      // Draw recipient text
      offCtx.save();
      offCtx.font = `${state.fontSize}px ${state.fontFamily}`;
      offCtx.fillStyle = state.textColor;
      offCtx.textAlign = getCanvasTextAlign(state.textAlign);
      offCtx.textBaseline = 'middle';
      offCtx.fillText(name, posX, posY);
      offCtx.restore();

      // Convert to blob and add to ZIP
      const blob = await new Promise((resolve) => offscreen.toBlob(resolve, 'image/png'));
      const safeName = sanitizeFilename(name, i);
      zip.file(`${safeName}.png`, blob);

      // Update progress
      const percent = Math.round(((i + 1) / total) * 100);
      progressStatus.textContent = `Generated ${i + 1} of ${total}: ${name}`;
      progressPercent.textContent = `${percent}%`;
      progressBar.style.width = `${percent}%`;

      // Allow UI thread to breathe
      if (i % 5 === 0) {
        await new Promise((r) => setTimeout(r, 0));
      }
    }

    progressStatus.textContent = "Compressing ZIP file...";
    const zipBlob = await zip.generateAsync({ type: 'blob' }, (metadata) => {
      progressPercent.textContent = `${Math.round(metadata.percent)}%`;
    });

    state.lastGeneratedBlob = zipBlob;
    triggerDownload(zipBlob, 'certificates.zip');

    // Confetti celebration
    confetti({
      particleCount: 80,
      spread: 70,
      origin: { y: 0.6 }
    });

    // Update UI state
    state.isGenerating = false;
    btnGenerate.disabled = false;
    btnGenerateLabel.textContent = "Generate Certificates (ZIP)";
    progressWrap.classList.add('visually-hidden');

    downloadBanner.classList.remove('visually-hidden');
    downloadCountText.textContent = `${total} certificate${total === 1 ? '' : 's'} bundled in ZIP`;

    animate(downloadBanner, { scale: [0.95, 1], opacity: [0, 1] }, { type: "spring", bounce: 0.3 });
  });

  btnDownloadAgain.addEventListener('click', () => {
    if (state.lastGeneratedBlob) {
      triggerDownload(state.lastGeneratedBlob, 'certificates.zip');
    }
  });
}

function sanitizeFilename(name, index) {
  const clean = name.replace(/[^a-zA-Z0-9_\-]/g, '_').replace(/_+/g, '_').trim();
  return clean || `certificate_${index + 1}`;
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

// ============================================================================
// Demo Certificate Generator for 1-Click Testing
// ============================================================================
function setupSampleDemoTrigger() {
  const demoBtn = document.createElement('button');
  demoBtn.type = 'button';
  demoBtn.className = 'btn-secondary';
  demoBtn.style.marginTop = '12px';
  demoBtn.textContent = '✨ Generate Sample Certificate Template';
  demoBtn.addEventListener('click', () => {
    generateDemoCertificate();
  });
  elements.stageEmptyState.appendChild(demoBtn);
}

function generateDemoCertificate() {
  const width = 1600;
  const height = 1100;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const dCtx = canvas.getContext('2d');

  // Background
  const gradient = dCtx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, '#fdfbf7');
  gradient.addColorStop(1, '#f4ece1');
  dCtx.fillStyle = gradient;
  dCtx.fillRect(0, 0, width, height);

  // Borders
  dCtx.strokeStyle = '#c5a059';
  dCtx.lineWidth = 14;
  dCtx.strokeRect(40, 40, width - 80, height - 80);

  dCtx.strokeStyle = '#1e293b';
  dCtx.lineWidth = 2;
  dCtx.strokeRect(60, 60, width - 120, height - 120);

  // Header Title
  dCtx.fillStyle = '#1e293b';
  dCtx.font = "bold 64px 'Playfair Display', serif";
  dCtx.textAlign = 'center';
  dCtx.fillText('CERTIFICATE OF ACHIEVEMENT', width / 2, 220);

  dCtx.font = "italic 26px 'Playfair Display', serif";
  dCtx.fillStyle = '#64748b';
  dCtx.fillText('This certificate is proudly presented to', width / 2, 360);

  // Underline for name
  dCtx.strokeStyle = '#cbd5e1';
  dCtx.lineWidth = 2;
  dCtx.beginPath();
  dCtx.moveTo(width / 2 - 350, 560);
  dCtx.lineTo(width / 2 + 350, 560);
  dCtx.stroke();

  // Description
  dCtx.font = "24px 'Plus Jakarta Sans', sans-serif";
  dCtx.fillStyle = '#475569';
  dCtx.fillText('For exceptional dedication, mastery, and performance throughout the program.', width / 2, 660);

  // Signatures
  dCtx.font = "bold 20px 'Plus Jakarta Sans', sans-serif";
  dCtx.fillText('Director of Certification', width / 4, 900);
  dCtx.fillText('Program Chairperson', (width / 4) * 3, 900);

  const img = new Image();
  img.onload = () => {
    setTemplateImage(img, "demo-certificate.png");
    state.normalizedPos = { x: 0.5, y: 0.46 }; // positioned right above the name line
    updateMarkerPosition();
    renderPreview();
  };
  img.src = canvas.toDataURL('image/png');
}

// Start app
window.addEventListener('DOMContentLoaded', init);
