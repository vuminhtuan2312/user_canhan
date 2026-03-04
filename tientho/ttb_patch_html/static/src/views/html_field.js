/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import {
    Component,
    useRef,
    onMounted,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { HtmlViewer } from "@html_editor/fields/html_viewer";
import { registry } from "@web/core/registry";

patch(HtmlViewer.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            if (this.readonlyElementRef) {
                const images = this.readonlyElementRef.el.querySelectorAll("img");
                images.forEach((image) => {
                    image.style.cursor = "zoom-in";
                    image.addEventListener("click", () => this.onClickImage(image))
                })
            }
        })
    },

    onClickImage(image) {
        let div = document.createElement("div");
        if (div) {
           div.classList.add("image-viewer-container")
           const imageViewer = div.appendChild(document.createElement("div"))
           imageViewer.classList.add("image-viewer")
           imageViewer.style.cursor = "zoom-out"

           const zoomedImage = imageViewer.appendChild(document.createElement("img"))
           zoomedImage.src = image.src

           document.body.appendChild(div)

           imageViewer.addEventListener("click", () => {
               console.log("removing image viewer...")
               div.remove()
           })
        }
    }
})




