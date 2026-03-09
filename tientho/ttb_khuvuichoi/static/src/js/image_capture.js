/** @odoo-module **/

import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { isBinarySize } from "@web/core/utils/binary";
import { rpc } from "@web/core/network/rpc";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState, onWillUpdateProps, useRef } from "@odoo/owl";
const { DateTime } = luxon;
export const fileTypeMagicWordMap = {
    "/": "jpg",
    R: "gif",
    i: "png",
    P: "svg+xml",
};

const placeholder = "/web/static/img/placeholder.png";
export function imageCacheKey(value) {
    if (value instanceof DateTime) {
        return value.ts;
    }
    return "";
}
class imageCapture extends Component {
    static template = "CaptureImage";
    static props = {
         ...standardFieldProps,
        enableZoom: { type: Boolean, optional: true },
        zoomDelay: { type: Number, optional: true },
        previewImage: { type: String, optional: true },
        acceptedFileExtensions: { type: String, optional: true },
        width: { type: Number, optional: true },
        height: { type: Number, optional: true },
        reload: { type: Boolean, optional: true },
    };
    static defaultProps = {
             acceptedFileExtensions: "image/*",
        reload: true,
    };
    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.isMobile = isMobileOS();
        const ua = typeof navigator !== "undefined" ? navigator.userAgent || "" : "";
        this.isOdooApp = /odoo/i.test(ua);
        this.isMobileBrowser = this.isMobile && !this.isOdooApp;
        this.state = useState({
            isValid: true,
            stream: null,
            /** Data URL ảnh vừa lưu để hiển thị ngay, không cần F5 */
            previewDataUrl: null,
            /** Trạng thái popup camera trên desktop/Odoo app */
            isDesktopModalOpen: false,
            hasSnapshot: false,
            /** Danh sách camera: [{ deviceId, label }] */
            videoDevices: [],
            /** deviceId đang chọn */
            selectedDeviceId: "",
        });
        this.player = useRef("player");
        this.capture = useRef("capture");
        this.camera = useRef("camera");
        this.save_image = useRef("save_image");
        this.mobileCameraInput = useRef("mobileCameraInput");
        this.desktopCaptureActions = useRef("desktopCaptureActions");
        this.snapshotCanvas = useRef("snapshotCanvas");
        this.imageInput = useRef("imageInput");
        this.desktopModal = useRef("desktopModal");
        this.rawCacheKey = this.props.record.data.write_date;
        onWillUpdateProps((nextProps) => {
            const { record } = this.props;
            const { record: nextRecord } = nextProps;
            if (record.resId !== nextRecord.resId || nextRecord.mode === "readonly") {
                this.rawCacheKey = nextRecord.data.write_date;
                this.state.previewDataUrl = null;
            }
        });
    }

    get sizeStyle() {
        // For getting image style details
        let style = "";
        if (this.props.width) {
            style += `max-width: ${this.props.width}px;`;
        }
        if (this.props.height) {
            style += `max-height: ${this.props.height}px;`;
        }
        return style;
    }
    get hasTooltip() {
    return (
            this.props.enableZoom && this.props.readonly && this.props.record.data[this.props.name]
        );
    }
    getUrl(previewFieldName) {
        // Ưu tiên ảnh vừa lưu (hiển thị ngay không cần F5)
        if (this.state.previewDataUrl) {
            return this.state.previewDataUrl;
        }
        if (!this.props.reload && this.lastURL) {
            return this.lastURL;
        }
        if (this.state.isValid && this.props.record.data[this.props.name]) {
            if (isBinarySize(this.props.record.data[this.props.name])) {
                if (!this.rawCacheKey) {
                    this.rawCacheKey = this.props.record.data.write_date;
                }
                this.lastURL = url("/web/image", {
                    model: this.props.record.resModel,
                    id: this.props.record.resId,
                    field: previewFieldName,
                    unique: imageCacheKey(this.rawCacheKey),
                });
            } else {
                // Use magic-word technique for detecting image type
                 const magic =
                    fileTypeMagicWordMap[this.props.record.data[this.props.name][0]] || "png";
                this.lastURL = `data:image/${magic};base64,${
                    this.props.record.data[this.props.name]
                }`;
            }
            return this.lastURL;
        }
        return placeholder;
    }
    onFileRemove() {
        this.state.isValid = true;
        this.state.previewDataUrl = null;
        this.props.record.update({ [this.props.name]: false });
    }
    async onFileUploaded(info) {
        this.state.isValid = true;
        this.rawCacheKey = null;
        // Base64 từ action_save_image (phần sau dấu phẩy) -> tạo data URL để hiển thị ngay
        const base64 = typeof info.data === "string" ? info.data : null;
        const dataUrl = base64 ? `data:image/png;base64,${base64}` : null;
        if (dataUrl) {
            this.state.previewDataUrl = dataUrl;
        }
        this.props.record.update({ [this.props.name]: info.data });
        try {
            await this.props.record.save();
            if (this.props.record.data.write_date) {
                this.rawCacheKey = this.props.record.data.write_date;
            }
            this.notification.add(_t("Đã lưu ảnh."), { type: "success" });
        } catch (err) {
            console.error("Save record failed:", err);
            this.notification.add(_t("Lưu form thất bại. Vui lòng nhấn Lưu thủ công."), { type: "warning" });
        }
    }
    /**
     * Click nút camera: mobile = mở input capture (chỉ camera), desktop = mở stream
     */
    onCameraClick() {
        if (this.isMobileBrowser) {
            this.mobileCameraInput.el.click();
        } else {
            this.OnClickOpenCamera();
        }
    }

    /**
     * Mobile: sau khi chụp xong từ input capture, gửi ảnh lên (không cho chọn file từ thư viện)
     */
    async onMobileCaptureChange(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file || !file.type.startsWith("image/")) return;
        const self = this;
        const reader = new FileReader();
        reader.onload = async function () {
            const dataUrl = reader.result;
            try {
                const results = await rpc("/web/dataset/call_kw", {
                    model: "image.capture",
                    method: "action_save_image",
                    args: [[], dataUrl],
                    kwargs: {},
                });
                const data = {
                    data: results,
                    name: file.name || "ImageFile.png",
                    objectUrl: null,
                    size: file.size,
                    type: file.type,
                };
                self.onFileUploaded(data);
            } catch (err) {
                console.error("Save image failed:", err);
                self.notification.add(_t("Không thể lưu ảnh"), { type: "danger" });
            }
            self.mobileCameraInput.el.value = "";
        };
        reader.readAsDataURL(file);
    }

    /**
     * Trả về thông báo thân thiện khi getUserMedia thất bại (từ chối quyền / chưa cấp).
     * Trên app mobile: khuyên vào Cài đặt > Ứng dụng > Quyền để bật camera.
     */
    _getCameraErrorMessage(error) {
        const name = error && error.name;
        if (name === "NotAllowedError" || name === "PermissionDeniedError") {
            return _t(
                "Quyền camera bị từ chối hoặc chưa bật. Vui lòng cho phép truy cập camera trong hộp thoại của thiết bị, hoặc vào Cài đặt > Ứng dụng > [Odoo] > Quyền và bật Camera."
            );
        }
        if (name === "NotFoundError") {
            return _t("Không tìm thấy camera. Vui lòng kiểm tra thiết bị.");
        }
        return error && error.message ? _t("Lỗi truy cập camera: ") + error.message : _t("Không thể truy cập camera.");
    }

    _getUserMedia() {
        if (typeof navigator === "undefined") return null;
        const mediaDevices = navigator.mediaDevices;
        if (mediaDevices && typeof mediaDevices.getUserMedia === "function") {
            return mediaDevices.getUserMedia.bind(mediaDevices);
        }
        const legacy = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
        if (typeof legacy === "function") {
            return (constraints) =>
                new Promise((resolve, reject) => {
                    legacy.call(navigator, constraints, resolve, reject);
                });
        }
        return null;
    }

    _getCameraUnavailableMessage() {
        const protocol = typeof location !== "undefined" ? (location.protocol || "").toLowerCase() : "";
        const isInsecure = protocol === "http:";
        if (isInsecure) {
            return _t(
                "Camera chỉ hoạt động khi truy cập qua HTTPS hoặc localhost. Bạn đang dùng HTTP. Vui lòng mở Odoo bằng địa chỉ https:// (ví dụ: https://tên-máy-chủ của bạn)."
            );
        }
        return _t(
            "Trình duyệt hoặc ứng dụng chưa hỗ trợ camera. Vui lòng dùng HTTPS hoặc kiểm tra quyền camera trong Cài đặt ứng dụng."
        );
    }

    /** Lấy danh sách thiết bị video (camera). Label có thể rỗng cho đến khi đã cấp quyền. */
    async _enumerateVideoDevices() {
        if (typeof navigator !== "undefined" && navigator.mediaDevices && typeof navigator.mediaDevices.enumerateDevices === "function") {
            const devices = await navigator.mediaDevices.enumerateDevices();
            return devices
                .filter((d) => d.kind === "videoinput")
                .map((d, i) => ({ deviceId: d.deviceId, label: d.label || _t("Camera") + " " + (i + 1) }));
        }
        return [];
    }

    /** Tạo constraints video theo deviceId đang chọn (chỉ phần video) */
    _getVideoConstraints() {
        const id = this.state.selectedDeviceId;
        if (id) {
            return { deviceId: { ideal: id } };
        }
        return { facingMode: "environment" };
    }

    /** Khởi tạo stream với camera đang chọn (hoặc mặc định) */
    async _startCameraStream(getUserMedia) {
        if (this.state.stream) {
            this.stopTracksOnMediaStream(this.state.stream);
            this.state.stream = null;
        }
        const videoConstraints = this._getVideoConstraints();
        this.state.stream = await getUserMedia({ video: videoConstraints, audio: false });
        this.player.el.srcObject = this.state.stream;
    }

    async OnClickOpenCamera() {
        const getUserMedia = this._getUserMedia();
        if (!getUserMedia) {
            this.notification.add(this._getCameraUnavailableMessage(), { type: "danger" });
            return;
        }
        try {
            if (this.state.stream) {
                this.stopTracksOnMediaStream(this.state.stream);
                this.state.stream = null;
            }
            this.state.isDesktopModalOpen = true;
            this.state.hasSnapshot = false;
            this.state.videoDevices = [];
            this.state.selectedDeviceId = "";
            this.desktopModal.el.classList.remove("d-none");
            this.player.el.classList.remove("d-none");
            this.snapshotCanvas.el.classList.add("d-none");
            this.desktopCaptureActions.el.classList.remove("d-none");
            this.desktopCaptureActions.el.classList.add("d-flex");
            this.camera.el.classList.add("d-none");
            // Bật stream mặc định với camera sau (environment)
            await this._startCameraStream(getUserMedia);
            const devices = await this._enumerateVideoDevices();
            this.state.videoDevices = devices;
            if (devices.length > 0) {
                // Giữ đúng camera đang dùng (đã là camera sau nhờ facingMode: "environment")
                const videoTrack = this.state.stream && this.state.stream.getVideoTracks()[0];
                const settings = videoTrack ? videoTrack.getSettings() : {};
                const currentDeviceId = settings.deviceId;
                this.state.selectedDeviceId = currentDeviceId || devices[0].deviceId;
                if (!currentDeviceId) {
                    await this._startCameraStream(getUserMedia);
                }
            }
        } catch (error) {
            console.error("Error accessing camera:", error);
            this.notification.add(this._getCameraErrorMessage(error), { type: "danger" });
        }
    }

    async onCameraDeviceChange(ev) {
        const deviceId = ev.target.value;
        if (deviceId === this.state.selectedDeviceId) return;
        this.state.selectedDeviceId = deviceId;
        const getUserMedia = this._getUserMedia();
        if (!getUserMedia) return;
        try {
            this.snapshotCanvas.el.classList.add("d-none");
            this.player.el.classList.remove("d-none");
            this.state.hasSnapshot = false;
            await this._startCameraStream(getUserMedia);
        } catch (error) {
            console.error("Error switching camera:", error);
            this.notification.add(_t("Không thể chuyển sang camera này."), { type: "danger" });
        }
    }
    stopTracksOnMediaStream(mediaStream) {
        for (const track of mediaStream.getTracks()) {
            track.stop();
        }
    }
    OnClickCaptureImage() {
        const video = this.player.el;
        const canvas = this.snapshotCanvas.el;
        const ctx = canvas.getContext("2d");
        if (!ctx || !video.videoWidth) return;
        const w = video.videoWidth;
        const h = video.videoHeight;
        canvas.width = w;
        canvas.height = h;
        ctx.drawImage(video, 0, 0, w, h);
        this.url = canvas.toDataURL("image/png");
        this.imageInput.el.value = this.url;
        canvas.classList.remove("d-none");
        video.classList.add("d-none");
        this.state.hasSnapshot = true;
    }
    OnClickRetake() {
        if (this.snapshotCanvas?.el && this.player?.el) {
            this.snapshotCanvas.el.classList.add("d-none");
            this.player.el.classList.remove("d-none");
        }
        this.state.hasSnapshot = false;
    }
    _cleanupDesktopCapture() {
        this.player.el.classList.add("d-none");
        this.snapshotCanvas.el.classList.add("d-none");
        this.desktopCaptureActions.el.classList.add("d-none");
        this.camera.el.classList.remove("d-none");
        this.desktopModal.el.classList.add("d-none");
        this.player.el.srcObject = null;
        if (this.state.stream) {
            this.stopTracksOnMediaStream(this.state.stream);
            this.state.stream = null;
        }
        this.state.isDesktopModalOpen = false;
        this.state.hasSnapshot = false;
        this.state.videoDevices = [];
        this.state.selectedDeviceId = "";
    }
    OnClickCloseModal() {
        this._cleanupDesktopCapture();
    }
    async OnClickSaveImage() {
        if (!this.url) return;
        const self = this;
        try {
            const results = await rpc("/web/dataset/call_kw", {
                model: "image.capture",
                method: "action_save_image",
                args: [[], this.url],
                kwargs: {},
            });
            const data = {
                data: results,
                name: "ImageFile.png",
                objectUrl: null,
                size: 0,
                type: "image/png",
            };
            self.onFileUploaded(data);
        } finally {
            this._cleanupDesktopCapture();
        }
    }
    onLoadFailed() {
        this.state.isValid = false;
        this.notification.add(_t("Could not display the selected image"), {
            type: "danger",
        });
    }
}
export const ImageCapture = {
    component: imageCapture,
     displayName: _t("Image"),
      supportedOptions: [
        {
            label: _t("Reload"),
            name: "reload",
            type: "boolean",
            default: true,
        },
        {
            label: _t("Enable zoom"),
            name: "zoom",
            type: "boolean",
        },
        {
            label: _t("Zoom delay"),
            name: "zoom_delay",
            type: "number",
            help: _t("Delay the apparition of the zoomed image with a value in milliseconds"),
        },
        {
            label: _t("Accepted file extensions"),
            name: "accepted_file_extensions",
            type: "string",
        },
        {
            label: _t("Size"),
            name: "size",
            type: "selection",
            choices: [
                { label: _t("Small"), value: "[0,90]" },
                { label: _t("Medium"), value: "[0,180]" },
                { label: _t("Large"), value: "[0,270]" },
            ],
        },
        {
            label: _t("Preview image"),
            name: "preview_image",
            type: "field",
            availableTypes: ["binary"],
        },
    ],
supportedTypes: ["binary"],
    fieldDependencies: [{ name: "write_date", type: "datetime" }],
    isEmpty: () => false,
    extractProps: ({ attrs, options }) => ({
        enableZoom: options.zoom,
        zoomDelay: options.zoom_delay,
        previewImage: options.preview_image,
        acceptedFileExtensions: options.accepted_file_extensions,
        width: options.size && Boolean(options.size[0]) ? options.size[0] : attrs.width,
        height: options.size && Boolean(options.size[1]) ? options.size[1] : attrs.height,
        reload: "reload" in options ? Boolean(options.reload) : true,
    }),
};
registry.category("fields").add("capture_image", ImageCapture);
