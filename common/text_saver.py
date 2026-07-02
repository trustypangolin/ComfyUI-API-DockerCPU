"""
Text File Saver for ComfyUI-API-DockerCPU

Provides a node to save text content to a file using a directory and
filename pair (typically from LoadImageWithMetadata). Useful for saving
sidecar text files (e.g., captions from a model API) next to source images.

- SaveTextWithFilename: Saves text to a file named after the source file.
"""

import os


class SaveTextWithFilename:
    """
    Save text content to a file using BASE_DIR and BASE_FILENAME inputs.

    Inputs:
        text:              The text content to save
        base_dir:          Directory where the file will be saved
        base_filename:     Source filename (used to derive the output name)
        replace_extension: If True, swap the source extension with `extension`
        extension:         New extension when replace_extension is True
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "forceInput": True}),
                "base_dir": ("STRING", {"forceInput": True}),
                "base_filename": ("STRING", {"forceInput": True}),
                "replace_extension": ("BOOLEAN", {"default": True}),
                "extension": ("STRING", {"default": "txt"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("saved_path",)
    FUNCTION = "save_text"
    OUTPUT_NODE = True
    CATEGORY = "🎨 DockerCPU API/Utilities"
    DESCRIPTION = "Saves text content to a file using BASE_DIR and BASE_FILENAME. Optionally replaces the file extension."

    def save_text(self, text, base_dir, base_filename, replace_extension=True, extension="txt"):
        name_without_ext = os.path.splitext(base_filename)[0]
        ext = extension.lstrip(".")

        if replace_extension:
            final_filename = f"{name_without_ext}.{ext}" if ext else name_without_ext
        else:
            final_filename = base_filename

        os.makedirs(base_dir, exist_ok=True)

        file_path = os.path.join(base_dir, final_filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        return (file_path,)


NODE_CLASS_MAPPINGS = {
    "SaveTextWithFilename": SaveTextWithFilename,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveTextWithFilename": "Save Text With Filename",
}
