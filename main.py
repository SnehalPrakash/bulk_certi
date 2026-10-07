import os
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont, ImageOps
import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(
    page_title="Bulk Certificate Generator",
    page_icon="🎓",
    layout="wide"
)

def sanitize_filename(name: str, index: int) -> str:
    """Sanitize participant name for safe filenames across all operating systems."""
    clean = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
    return clean if clean else f"certificate_{index + 1}"

def load_font(font_file, font_size: int):
    """Load either the uploaded font or default america.ttf font safely."""
    try:
        if font_file is not None:
            font_bytes = io.BytesIO(font_file.getvalue())
            return ImageFont.truetype(font_bytes, font_size)
        elif os.path.exists("america.ttf"):
            return ImageFont.truetype("america.ttf", font_size)
        else:
            return ImageFont.load_default()
    except Exception as e:
        st.warning(f"Error loading custom font, falling back to default: {e}")
        return ImageFont.load_default()

def draw_name_on_certificate(
    base_image: Image.Image,
    name: str,
    x: int,
    y: int,
    font,
    color: str = "#000000",
    alignment: str = "Center"
) -> Image.Image:
    """Draw participant name on a copy of the base certificate."""
    cert = base_image.copy()
    draw = ImageDraw.Draw(cert)
    
    if alignment == "Center":
        draw.text((x, y), name, fill=color, font=font, anchor="mm")
    else:
        draw.text((x, y), name, fill=color, font=font)
        
    return cert

def main():
    st.title("🎓 Bulk Certificate Generator")
    st.markdown(
        "Upload your certificate template, click on the image to set the name placement, "
        "and generate bulk personalized certificates in seconds."
    )

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.subheader("1. Setup & Styling")
        image_file = st.file_uploader(
            "Upload Certificate Template",
            type=["png", "jpg", "jpeg", "webp", "bmp", "tiff"],
            help="Upload an image template without recipient names."
        )

        font_col1, font_col2 = st.columns([2, 1])
        with font_col1:
            font_file = st.file_uploader(
                "Upload Custom Font (.ttf)",
                type=["ttf"],
                help="Leave empty to use default 'america.ttf'."
            )
        with font_col2:
            font_size = st.number_input(
                "Font Size",
                min_value=8,
                max_value=300,
                value=48,
                step=2
            )

        style_col1, style_col2 = st.columns(2)
        with style_col1:
            text_color = st.color_picker("Text Color", "#000000")
        with style_col2:
            alignment = st.radio(
                "Text Alignment",
                ["Center", "Left"],
                index=0,
                horizontal=True,
                help="Center aligns the name horizontally around the click position (recommended)."
            )

        st.subheader("2. Recipient Names")
        names_text = st.text_area(
            "Enter Names (one per line)",
            placeholder="John Doe\nJane Smith\nAlex Johnson",
            height=160
        )
        
        raw_names = [n.strip() for n in names_text.split("\n") if n.strip()]
        if raw_names:
            st.caption(f"✓ Found **{len(raw_names)}** recipient name(s).")

    with col_right:
        st.subheader("3. Coordinate Selection & Live Preview")
        
        if image_file is None:
            st.info("👈 Please upload a certificate template to select coordinates and preview.")
            return

        # Load and normalize base template
        try:
            base_image = ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")
        except Exception as e:
            st.error(f"Failed to open image file: {e}")
            return

        orig_w, orig_h = base_image.size
        st.caption(f"Template Dimensions: **{orig_w} × {orig_h} px**")

        # Initialize session state for coordinates
        if "coord_x" not in st.session_state:
            st.session_state["coord_x"] = orig_w // 2
        if "coord_y" not in st.session_state:
            st.session_state["coord_y"] = orig_h // 2
        if "_last_click_time" not in st.session_state:
            st.session_state["_last_click_time"] = None

        st.markdown("**Click on the template image to set the name placement:**")
        
        # Interactive clickable image
        coords = streamlit_image_coordinates(
            base_image,
            key="cert_canvas",
            cursor="crosshair"
        )

        # Detect new clicks and map from display coordinates to original image coordinates
        if coords is not None:
            click_time = coords.get("unix_time")
            if click_time != st.session_state["_last_click_time"]:
                st.session_state["_last_click_time"] = click_time
                disp_w = coords.get("width") or orig_w
                disp_h = coords.get("height") or orig_h
                scale_x = orig_w / disp_w if disp_w > 0 else 1.0
                scale_y = orig_h / disp_h if disp_h > 0 else 1.0
                st.session_state["coord_x"] = int(coords["x"] * scale_x)
                st.session_state["coord_y"] = int(coords["y"] * scale_y)
                st.rerun()

        # Coordinate numeric adjustment controls
        c_x, c_y = st.columns(2)
        with c_x:
            current_x = st.number_input(
                "X Coordinate",
                min_value=0,
                max_value=orig_w,
                value=int(st.session_state["coord_x"]),
                step=2,
                key="input_coord_x"
            )
            st.session_state["coord_x"] = current_x
        with c_y:
            current_y = st.number_input(
                "Y Coordinate",
                min_value=0,
                max_value=orig_h,
                value=int(st.session_state["coord_y"]),
                step=2,
                key="input_coord_y"
            )
            st.session_state["coord_y"] = current_y

        st.success(f"📍 Selected Position: **X = {st.session_state['coord_x']}, Y = {st.session_state['coord_y']}**")

        # Live Preview
        font = load_font(font_file, font_size)
        preview_name = raw_names[0] if raw_names else "Sample Recipient Name"
        
        preview_cert = draw_name_on_certificate(
            base_image,
            preview_name,
            st.session_state["coord_x"],
            st.session_state["coord_y"],
            font,
            text_color,
            alignment
        )

        st.markdown("**Live Preview:**")
        st.image(
            preview_cert,
            caption=f"Preview with text: '{preview_name}'",
            use_container_width=True
        )

    # 4. Generate Section
    st.divider()
    st.subheader("4. Generate Certificates")

    if not raw_names:
        st.warning("Please enter at least one recipient name to generate certificates.")
        return

    if st.button("🚀 Generate Certificates", type="primary", use_container_width=True):
        progress_bar = st.progress(0, text="Generating certificates...")
        zip_buffer = io.BytesIO()
        preview_gallery = []

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            total = len(raw_names)
            for idx, name in enumerate(raw_names):
                cert_img = draw_name_on_certificate(
                    base_image,
                    name,
                    st.session_state["coord_x"],
                    st.session_state["coord_y"],
                    font,
                    text_color,
                    alignment
                )
                
                # Save into zip
                img_byte_arr = io.BytesIO()
                cert_img.save(img_byte_arr, format="PNG")
                filename = f"{sanitize_filename(name, idx)}.png"
                zip_file.writestr(filename, img_byte_arr.getvalue())

                # Collect a few samples for preview gallery
                if idx < 4:
                    preview_gallery.append((name, cert_img))

                # Update progress
                progress_bar.progress((idx + 1) / total, text=f"Generated {idx + 1}/{total}: {name}")

        progress_bar.empty()
        st.success(f"🎉 Successfully generated **{len(raw_names)}** certificates!")

        # Download button
        st.download_button(
            label="📥 Download All Certificates (.zip)",
            data=zip_buffer.getvalue(),
            file_name="certificates.zip",
            mime="application/zip",
            use_container_width=True
        )

        # Show samples
        if preview_gallery:
            st.markdown("### Generated Samples Preview")
            sample_cols = st.columns(min(len(preview_gallery), 4))
            for i, (p_name, p_img) in enumerate(preview_gallery):
                with sample_cols[i]:
                    st.image(p_img, caption=p_name, use_container_width=True)

if __name__ == "__main__":
    main()