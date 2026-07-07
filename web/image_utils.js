import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function findWidget(node, name) {
    return node.widgets?.find((widget) => widget.name === name);
}

function setComboValues(widget, values) {
    widget.options = widget.options || {};
    widget.options.values = values;
}

app.registerExtension({
    name: "ComfyUI-API-DockerCPU.LoadImageWithMetadata",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "LoadImageWithMetadata") {
            return;
        }

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            const folderTypeWidget = findWidget(this, "folder_type");
            const imageWidget = findWidget(this, "image");
            if (!folderTypeWidget || !imageWidget) {
                return result;
            }

            const setImageUploadEnabled = (enabled) => {
                imageWidget.options = imageWidget.options || {};
                if (enabled) {
                    imageWidget.options.image_upload = true;
                } else {
                    delete imageWidget.options.image_upload;
                }
            };

            const refreshFiles = async () => {
                const previous = imageWidget.value;
                const folderType = folderTypeWidget.value || "input";
                const params = new URLSearchParams({ folder_type: folderType });

                // Only the input folder supports upload + preview in ComfyUI's frontend.
                // For output, use a plain combo so we don't show a misleading preview
                // from the input folder.
                setImageUploadEnabled(folderType === "input");

                try {
                    const response = await api.fetchApi(`/dockercpu/load_image_with_metadata/files?${params.toString()}`);
                    if (!response.ok) {
                        throw new Error(await response.text());
                    }
                    const payload = await response.json();
                    const files = Array.isArray(payload.files) ? payload.files : [];
                    setComboValues(imageWidget, files);
                    imageWidget.value = files.includes(previous) ? previous : (files[0] || "");
                } catch (error) {
                    console.error("LoadImageWithMetadata file refresh failed", error);
                }
                this.setDirtyCanvas(true, true);
            };

            // Apply initial state based on default folder_type
            setImageUploadEnabled((folderTypeWidget.value || "input") === "input");

            const callback = folderTypeWidget.callback;
            folderTypeWidget.callback = function () {
                const value = callback?.apply(this, arguments);
                refreshFiles();
                return value;
            };

            return result;
        };
    },
});
