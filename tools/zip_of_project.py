import os
import zipfile


def zip_dir(src_dir, zip_filename, exclude_patterns):
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            # Exclude directories
            dirs[:] = [d for d in dirs if not any(
                exc in d or d.startswith(exc.lstrip('.')) for exc in exclude_patterns if exc.endswith('/'))]

            for file in files:
                # Exclude files
                if any(file == exc or file.startswith(exc) for exc in exclude_patterns if not exc.endswith('/')):
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, src_dir)
                zf.write(full_path, rel_path)
    print(f"Zip created: {zip_filename} (excluded: {', '.join(exclude_patterns)})")


# Run it
exclude = ['.env', '.venv1/', '.idea/', '__pycache__/']
zip_dir('.', '../ProQuery_v1.1_clean.zip', exclude)