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
export function isWebMBase64(data) {
    return typeof data === "string" && data.length >= 2 && data.substring(0, 2) === "Gk";
}

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
        /** Tên field lưu loại media ('image' | 'video') để hiển thị đúng khi mở lại */
        mediaTypeField: { type: String, optional: true },
        /** Nếu true: lưu qua RPC action_append_proof_media rồi clear field (tránh payload lớn qua form) */
        appendViaRpc: { type: Boolean, optional: true },
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
            /** Data URL ảnh/video vừa lưu để hiển thị ngay, không cần F5 */
            previewDataUrl: null,
            /** Trạng thái popup camera trên desktop/Odoo app */
            isDesktopModalOpen: false,
            hasSnapshot: false,
            /** Danh sách camera: [{ deviceId, label }] */
            videoDevices: [],
            /** deviceId đang chọn */
            selectedDeviceId: "",
            /** Chế độ: 'photo' (chụp ảnh) hoặc 'video' (quay video) */
            captureMode: "photo",
            /** Đang ghi hình (video) */
            isRecording: false,
            /** Thời gian quay (giây) để hiển thị 00:00 */
            recordingDurationSeconds: 0,
        });
        this.recordingStartTime = null;
        this.recordingTimerId = null;
        this.player = useRef("player");
        this.capture = useRef("capture");
        this.camera = useRef("camera");
        this.save_image = useRef("save_image");
        this.mobileCameraInput = useRef("mobileCameraInput");
        this.mobileVideoInput = useRef("mobileVideoInput");
        this.desktopCaptureActions = useRef("desktopCaptureActions");
        this.snapshotCanvas = useRef("snapshotCanvas");
        this.imageInput = useRef("imageInput");
        this.desktopModal = useRef("desktopModal");
        /** MediaRecorder và buffer khi quay video */
        this.mediaRecorder = null;
        this.recordedChunks = [];
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
    /** Định dạng thời gian quay: MM:SS */
    get recordingDurationFormatted() {
        const s = this.state.recordingDurationSeconds || 0;
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
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
            const data = this.props.record.data[this.props.name];
            if (isBinarySize(data)) {
                if (!this.rawCacheKey) {
                    this.rawCacheKey = this.props.record.data.write_date;
                }
                const typeField = this.props.mediaTypeField;
                const isVideoBinary =
                    typeField && this.props.record.data[typeField] === "video";
                this.lastURL = url(
                    isVideoBinary ? "/web/binary/proof" : "/web/image",
                    {
                        model: this.props.record.resModel,
                        id: this.props.record.resId,
                        field: previewFieldName,
                        unique: imageCacheKey(this.rawCacheKey),
                    }
                );
            } else {
                const raw = typeof data === "string" ? data : "";
                if (isWebMBase64(raw)) {
                    this.lastURL = `data:video/webm;base64,${raw}`;
                } else {
                    const magic =
                        fileTypeMagicWordMap[raw[0]] || "png";
                    this.lastURL = `data:image/${magic};base64,${raw}`;
                }
            }
            return this.lastURL;
        }
        return placeholder;
    }
    get isVideo() {
        const urlStr = this.state.previewDataUrl || this.lastURL || "";
        if (typeof urlStr === "string" && urlStr.startsWith("data:video/")) return true;
        const data = this.props.record.data[this.props.name];
        if (!isBinarySize(data) && typeof data === "string" && isWebMBase64(data)) return true;
        const typeField = this.props.mediaTypeField;
        return !!(typeField && this.props.record.data[typeField] === "video");
    }
    onFileRemove() {
        this.state.isValid = true;
        this.state.previewDataUrl = null;
        this.props.record.update({ [this.props.name]: false });
    }
    async onFileUploaded(info) {
        this.state.isValid = true;
        this.rawCacheKey = null;
        const base64 = typeof info.data === "string" ? info.data : null;
        const isVideo = (info.type && info.type.startsWith("video/")) || this.state.captureMode === "video";
        const mimeType = info.type || (isVideo ? "video/webm" : "image/png");
        const dataUrl = base64 ? `data:${mimeType};base64,${base64}` : null;
        if (dataUrl) {
            this.state.previewDataUrl = dataUrl;
        }
        if (this.props.appendViaRpc && this.props.record.resModel && this.props.record.resId && base64) {
            try {
                await rpc("/web/dataset/call_kw", {
                    model: this.props.record.resModel,
                    method: "action_append_proof_media",
                    args: [this.props.record.resId, base64, isVideo ? "video" : "image"],
                    kwargs: {},
                });
                this.props.record.update({
                    [this.props.name]: false,
                    ...(this.props.mediaTypeField && { [this.props.mediaTypeField]: false }),
                });
                await this.props.record.save();
                this.state.previewDataUrl = null;
                if (this.props.record.data.write_date) {
                    this.rawCacheKey = this.props.record.data.write_date;
                }
                this.notification.add(isVideo ? _t("Đã lưu video.") : _t("Đã lưu ảnh."), { type: "success" });
            } catch (err) {
                console.error("Append proof media failed:", err);
                this.notification.add(err?.message || _t("Không thể lưu minh chứng."), { type: "danger" });
            }
            return;
        }
        const updates = { [this.props.name]: info.data };
        if (this.props.mediaTypeField) {
            updates[this.props.mediaTypeField] = isVideo ? "video" : "image";
        }
        this.props.record.update(updates);
        try {
            await this.props.record.save();
            if (this.props.record.data.write_date) {
                this.rawCacheKey = this.props.record.data.write_date;
            }
            this.notification.add(isVideo ? _t("Đã lưu video.") : _t("Đã lưu ảnh."), { type: "success" });
        } catch (err) {
            console.error("Save record failed:", err);
            this.notification.add(_t("Lưu form thất bại. Vui lòng nhấn Lưu thủ công."), { type: "warning" });
        }
    }
    /**
     * Click nút camera: mobile = mở input capture (chỉ camera / camcorder), desktop = mở stream
     */
    onCameraClick(ev) {
        const mode = ev?.currentTarget?.dataset?.mode === "video" ? "video" : "photo";
        this.state.captureMode = mode;
        if (this.isMobileBrowser) {
            if (mode === "video" && this.mobileVideoInput?.el) {
                this.mobileVideoInput.el.click();
            } else if (this.mobileCameraInput?.el) {
                this.mobileCameraInput.el.click();
            }
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
            if (self.mobileCameraInput?.el) {
                self.mobileCameraInput.el.value = "";
            }
        };
        reader.readAsDataURL(file);
    }

    /**
     * Mobile: sau khi quay xong từ input capture video, gửi file video lên
     */
    async onMobileVideoChange(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file || !file.type.startsWith("video/")) return;
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
                    name: file.name || "VideoFile.webm",
                    objectUrl: null,
                    size: file.size,
                    type: file.type || "video/webm",
                };
                self.onFileUploaded(data);
            } catch (err) {
                console.error("Save video failed:", err);
                self.notification.add(_t("Không thể lưu video"), { type: "danger" });
            }
            if (self.mobileVideoInput?.el) {
                self.mobileVideoInput.el.value = "";
            }
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
        const wantsAudio = this.state.captureMode === "video";
        this.state.stream = await getUserMedia({ video: videoConstraints, audio: wantsAudio });
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

    /**
     * Đổi camera: nếu đang quay thì chỉ thay video track trong stream hiện tại (ghi hình không dừng).
     * Nếu không quay thì đổi stream như cũ.
     */
    async onCameraDeviceChange(ev) {
        const deviceId = ev.target.value;
        if (deviceId === this.state.selectedDeviceId) return;
        const getUserMedia = this._getUserMedia();
        if (!getUserMedia) return;
        this.state.selectedDeviceId = deviceId;
        try {
            this.snapshotCanvas.el.classList.add("d-none");
            this.player.el.classList.remove("d-none");
            this.state.hasSnapshot = false;
            if (this.state.isRecording && this.state.stream && this.mediaRecorder && this.mediaRecorder.state === "recording") {
                await this._replaceVideoTrackWhileRecording(getUserMedia);
            } else {
                await this._startCameraStream(getUserMedia);
            }
        } catch (error) {
            console.error("Error switching camera:", error);
            this.notification.add(_t("Không thể chuyển sang camera này."), { type: "danger" });
        }
    }
    /**
     * Thay chỉ video track trong stream đang ghi, để MediaRecorder không bị dừng.
     */
    async _replaceVideoTrackWhileRecording(getUserMedia) {
        const newStream = await getUserMedia({
            video: this._getVideoConstraints(),
            audio: this.state.captureMode === "video",
        });
        const currentStream = this.state.stream;
        const newVideoTrack = newStream.getVideoTracks()[0];
        const oldVideoTrack = currentStream.getVideoTracks()[0];
        if (!oldVideoTrack || !newVideoTrack) {
            this.stopTracksOnMediaStream(newStream);
            return;
        }
        currentStream.removeTrack(oldVideoTrack);
        currentStream.addTrack(newVideoTrack);
        oldVideoTrack.stop();
        newStream.getAudioTracks().forEach((t) => t.stop());
        this.player.el.srcObject = currentStream;
    }
    stopTracksOnMediaStream(mediaStream) {
        for (const track of mediaStream.getTracks()) {
            track.stop();
        }
    }
    async OnClickStartRecording() {
        if (this.state.captureMode !== "video") {
            return;
        }
        const getUserMedia = this._getUserMedia();
        if (!getUserMedia) {
            this.notification.add(this._getCameraUnavailableMessage(), { type: "danger" });
            return;
        }
        try {
            if (!this.state.stream) {
                await this._startCameraStream(getUserMedia);
            }
            this.recordedChunks = [];
            let options;
            try {
                options = { mimeType: "video/webm;codecs=vp8,opus" };
                // Một số trình duyệt có thể không hỗ trợ mimeType cụ thể
                // trong trường hợp đó sẽ ném lỗi và ta fallback ở catch.
                // eslint-disable-next-line no-new
                new MediaRecorder(this.state.stream, options);
            } catch {
                options = undefined;
            }
            this.mediaRecorder = new MediaRecorder(this.state.stream, options);
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                }
            };
            this.mediaRecorder.onstop = () => {
                const blob = new Blob(this.recordedChunks, { type: "video/webm" });
                const reader = new FileReader();
                reader.onloadend = () => {
                    this.url = reader.result; // data:video/webm;base64,...
                    this.state.hasSnapshot = true;
                };
                reader.readAsDataURL(blob);
            };
            this.mediaRecorder.start();
            this.state.isRecording = true;
            this.state.hasSnapshot = false;
            this.recordingStartTime = Date.now();
            this.state.recordingDurationSeconds = 0;
            if (this.recordingTimerId) clearInterval(this.recordingTimerId);
            this.recordingTimerId = setInterval(() => {
                if (!this.recordingStartTime) return;
                this.state.recordingDurationSeconds = Math.floor(
                    (Date.now() - this.recordingStartTime) / 1000
                );
            }, 1000);
        } catch (error) {
            console.error("Error starting recording:", error);
            this.notification.add(_t("Không thể bắt đầu quay video."), { type: "danger" });
        }
    }
    _clearRecordingTimer() {
        if (this.recordingTimerId) {
            clearInterval(this.recordingTimerId);
            this.recordingTimerId = null;
        }
        this.recordingStartTime = null;
        this.state.recordingDurationSeconds = 0;
    }
    OnClickStopRecording() {
        if (this.mediaRecorder && this.state.isRecording) {
            this.mediaRecorder.stop();
        }
        this.state.isRecording = false;
        this._clearRecordingTimer();
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
        if (this.mediaRecorder && this.state.isRecording) {
            try {
                this.mediaRecorder.stop();
            } catch {
                // bỏ qua lỗi khi dừng recorder
            }
        }
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this._clearRecordingTimer();
        this.state.isDesktopModalOpen = false;
        this.state.hasSnapshot = false;
        this.state.isRecording = false;
        this.state.recordingDurationSeconds = 0;
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
                name: this.state.captureMode === "video" ? "VideoFile.webm" : "ImageFile.png",
                objectUrl: null,
                size: 0,
                type: this.state.captureMode === "video" ? "video/webm" : "image/png",
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
    onVideoLoadFailed() {
        this.state.isValid = false;
        this.notification.add(_t("Could not play the selected video"), {
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
        mediaTypeField: options.media_type_field || undefined,
        appendViaRpc: Boolean(options.append_via_rpc),
    }),
};
registry.category("fields").add("capture_image", ImageCapture);
