def save_file(file_obj, dest_path):
    # placeholder: write file to dest_path
    with open(dest_path, "wb") as f:
        f.write(file_obj.read())
    return True
