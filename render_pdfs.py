import os
import sys
import json
import time
import shutil

def install_pymupdf_if_needed():
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        try:
            import fitz
            return fitz
        except ImportError:
            import subprocess
            print("PyMuPDF not found. Installing...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf"])
                import fitz
                print("PyMuPDF installed successfully.")
                return fitz
            except Exception as e:
                print(f"Failed to install PyMuPDF: {e}")
                sys.exit(1)

def main():
    fitz = install_pymupdf_if_needed()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(current_dir, "dist")
    output_base_dir = os.path.join(dist_dir, "rendered")
    
    # Create dist and dist/rendered directories
    os.makedirs(output_base_dir, exist_ok=True)
    
    # Copy static web assets to dist/
    static_assets = ["index.html", "viewer.html", "LogoWM.png", "config.json"]
    for asset in static_assets:
        src = os.path.join(current_dir, asset)
        dst = os.path.join(dist_dir, asset)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"Copied static asset: {asset}")
            
    # Scan for PDF files in the root folder
    pdf_files = [f for f in os.listdir(current_dir) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        print("No PDF files found in workspace root.")
        return
        
    print(f"Found {len(pdf_files)} PDF files. Compiling to dist/...")
    
    for filename in sorted(pdf_files):
        pdf_path = os.path.join(current_dir, filename)
        pdf_basename = os.path.splitext(filename)[0]
        pdf_output_dir = os.path.join(output_base_dir, pdf_basename)
        manifest_path = os.path.join(pdf_output_dir, "manifest.json")
        
        # Copy the raw PDF to dist/ (so download links work)
        dst_pdf = os.path.join(dist_dir, filename)
        shutil.copy2(pdf_path, dst_pdf)
        
        # Skip rendering if already compiled and manifest is newer than PDF
        if os.path.exists(manifest_path):
            pdf_mtime = os.path.getmtime(pdf_path)
            manifest_mtime = os.path.getmtime(manifest_path)
            if manifest_mtime > pdf_mtime:
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f_mf:
                        m_data = json.load(f_mf)
                        pages_count = m_data.get("pagesCount", 0)
                        all_exist = True
                        for i in range(pages_count):
                            if not os.path.exists(os.path.join(pdf_output_dir, f"page-{i + 1}.jpg")):
                                all_exist = False
                                break
                        if all_exist:
                            print(f"Skipping (already compiled): {filename}")
                            continue
                except:
                    pass
        
        print(f"\nProcessing: {filename}")
        t_start = time.time()
        
        try:
            os.makedirs(pdf_output_dir, exist_ok=True)
            doc = fitz.open(pdf_path)
            pages_count = len(doc)
            
            pages_info = []
            
            for page_idx in range(pages_count):
                page = doc[page_idx]
                
                # Render to high quality image (DPI 150)
                pix = page.get_pixmap(dpi=150)
                
                img_name = f"page-{page_idx + 1}.jpg"
                img_path = os.path.join(pdf_output_dir, img_name)
                
                # Save as jpeg
                pix.save(img_path)
                
                pages_info.append({
                    "width": pix.width,
                    "height": pix.height
                })
                
                sys.stdout.write(f"\r  -> Rendered page {page_idx + 1}/{pages_count}")
                sys.stdout.flush()
                
            # Write manifest.json
            manifest_data = {
                "pagesCount": pages_count,
                "width": pages_info[0]["width"] if pages_info else 0,
                "height": pages_info[0]["height"] if pages_info else 0,
                "pages": pages_info
            }
            
            with open(manifest_path, "w", encoding="utf-8") as f_manifest:
                json.dump(manifest_data, f_manifest, indent=2)
                
            t_duration = time.time() - t_start
            sys.stdout.write(f"\n  Done: {pages_count} pages in {t_duration:.1f} seconds.\n")
            sys.stdout.flush()
            
        except Exception as err:
            print(f"\n  Error processing {filename}: {err}")

if __name__ == "__main__":
    main()
