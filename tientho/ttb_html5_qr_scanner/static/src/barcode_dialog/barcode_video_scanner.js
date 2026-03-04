/** @odoo-module **/

import { loadJS } from "@web/core/assets";
import { delay } from "@web/core/utils/concurrency";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { pick } from "@web/core/utils/objects";
import { _t } from "@web/core/l10n/translation";
import { CropOverlay } from "@web/core/barcode/crop_overlay";
import { isVideoElementReady as isZxingVideoElementReady, buildZXingBarcodeDetector } from "@web/core/barcode/ZXingBarcodeDetector";
import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";

const ZXING_LIB_PATH = "/web/static/lib/zxing-library/zxing-library.js";
const HTML5_QR_SCANNER =  "/ttb_html5_qr_scanner/static/assets/js/html5qr_code.js"

export class CustomBarcodeVideoScanner extends Component {
    static template = "ttb_html5_qr_scanner.CustomBarcodeVideoScanner";
    static components = {
        CropOverlay,
    };
    static props = {
        cssClass: { type: String, optional: true },
        facingMode: {
            type: String,
            validate: (fm) => ["environment", "left", "right", "user"].includes(fm),
            optional: true,
        },
        onResult: { type: Function },
        onError: { type: Function },
        close: { type: Function, optional: true},
        delayBetweenScan: { type: Number, optional: true },
        useHtml5QrScanner: { type: Boolean, optional: true }, // This prop now dictates behavior
    };
    static defaultProps = {
        cssClass: "w-100 h-100",
        facingMode: "environment",
        delayBetweenScan: 200,
        useHtml5QrScanner: true, // Default to attempting HTML5 QR
    };

    setup() {
        this.state = useState({
            isZxingReady: false,
            html5QrError: null, // Not used for display in this component anymore, onError handles it
            availableCameras: [],
            selectedCamera: "",
        });

        this.html5QrCodeScanner = null;
        this._html5ScannerStarted = false;
        this.zxingDetector = null;
        this.zxingStream = null;
        this.zxingDetectorTimeout = null;
        this.zxingScanPaused = false;
        this.zxingOverlayInfo = {};
        this.zxingZoomRatio = 1;

        // Refs are conditional based on which scanner is active
        this.qrScannerElementRef = useRef("qrScannerElement"); // For HTML5
        this.videoPreviewRef = useRef("videoPreview");       // For ZXing
        this.videoElementContainer = useRef("videoElementContainer"); // For ZXing
        this.cameraOptions = useRef("cameraOptions");

        onWillStart(async () => {
            if (this.props.useHtml5QrScanner) {
                try {
                    await loadJS(HTML5_QR_SCANNER);
                } catch (e) {
                    console.error("Failed to load Html5Qrcode library:", e);
                    throw new Error(`Failed to load HTML5_QRCODE_PATH`);
                }
            } else { // ZXing/Native path
                let DetectorClass;
                // Try Native BarcodeDetector first
                if ("BarcodeDetector" in window) {
                    try {
                        const formats = await BarcodeDetector.getSupportedFormats();
                        if (formats && formats.length > 0) {
                            DetectorClass = BarcodeDetector;
                        } else {
                            throw new Error("Native BarcodeDetector supports no formats.");
                        }
                    } catch (e) {
                        console.warn("Native BarcodeDetector not fully available or supports no formats, trying ZXing.", e);
                        // Fallback to ZXing
                        await loadJS(ZXING_LIB_PATH);
                        DetectorClass = buildZXingBarcodeDetector(window.ZXing);
                    }
                } else { // Native not available, directly use ZXing
                    await loadJS(ZXING_LIB_PATH);
                    DetectorClass = buildZXingBarcodeDetector(window.ZXing);
                }
                const formats = await DetectorClass.getSupportedFormats();
                this.zxingDetector = new DetectorClass({ formats });
            }
        });

        onMounted(async () => {
            // A small delay to ensure DOM is fully ready, especially refs.
            await delay(0);
            if (this.props.useHtml5QrScanner) {
                 try {
                    const devices = await Html5Qrcode.getCameras();
                    if (devices && devices.length) {
                        for (const device of devices) {
                            this.state.availableCameras.push(device);
                        }
                    }
                } catch (err) {
                    console.error('Failed to get device ids', err);
                }
                await this.startHtml5Scanner();
            } else {
                try {
                    const devices = await browser.navigator.mediaDevices.enumerateDevices();
                    if (devices && devices.length) {
                        for (const device of devices) {
                            if (device.kind !== 'audiooutput' && device.kind !== 'audioinput' ) {
                                this.state.availableCameras.push(device);
                            }
                        }
                    }
                } catch (err) {
                    console.error('Failed to get device ids', err);
                }
                await this.startZxingScanner();
            }
        });

        onWillUnmount(async () => {
            if (this.props.useHtml5QrScanner) {
                await this.stopHtml5Scanner();
            } else {
                this.stopZxingScanner();
            }
        });
    }
    async onSelect(ev) {
        this.state.selectedCamera = ev.target.value;
        await this.startHtml5Scanner();
    }

    // --- HTML5-QRCode Scanner Methods ---
    async startHtml5Scanner() {
        if (typeof Html5Qrcode === "undefined") {
            const errorMessage = _t("Html5Qrcode library not loaded. Cannot start scanner.");
            this.props.onError(new Error(errorMessage)); // Critical error, triggers fallback
            return;
        }
        if (!this.qrScannerElementRef.el) {
            // Wait a tick in case element is not ready immediately (though ref should ensure it)
            await delay(50);
            if (!this.qrScannerElementRef.el) {
                 const errorMessage = _t("HTML5 QR Scanner DOM element not found.");
                 this.props.onError(new Error(errorMessage)); // Critical error, triggers fallback
                 return;
            }
        }

        // Ensure the element has an ID for Html5Qrcode
        const elementId = "html5-qr-reader-placeholder";
        if (this.qrScannerElementRef.el && !this.qrScannerElementRef.el.id) {
            this.qrScannerElementRef.el.id = elementId;
        }

        this.html5QrCodeScanner = new Html5Qrcode(this.qrScannerElementRef.el.id, { verbose: false });

        const config = {
            fps: 10, // Increased FPS for potentially better responsiveness
        };

        const qrCodeSuccessCallback = (decodedText, decodedResult) => {
            if (!this._html5ScannerStarted) return;
            console.log(decodedText, decodedResult);
            this.props.onResult(decodedText);
        };

        const device = this.state.selectedCamera || this.state.availableCameras[0].id;
        try {
            await this.html5QrCodeScanner.start(
                device,
                config,
                qrCodeSuccessCallback,
                (errorMessage) => { /* Per-frame scan errors, usually ignored */ }
            );
            this._html5ScannerStarted = true;
        } catch (err) {
            console.error("Failed to start HTML5 QR scanner:", err);
            const friendlyMessage = err.name === "NotAllowedError" ?
                _t("Camera permission denied. Please allow camera access.") :
                _t("Could not start HTML5 QR scanner: %(message)s", { message: err.message || err.name });
            this.props.onError(new Error(friendlyMessage)); // This will trigger fallback in BarcodeDialog
        }
    }

    async stopHtml5Scanner() {
        if (this.html5QrCodeScanner && this._html5ScannerStarted) {
            try {
                await this.html5QrCodeScanner.stop();
            } catch (err) {
                console.warn("Error stopping HTML5 QR Code scanner, possibly already stopped or element removed:", err);
            } finally {
                this._html5ScannerStarted = false;
                this.html5QrCodeScanner = null;
            }
        }
    }

    // --- ZXing/Native Scanner Methods (largely unchanged) ---

    async onSelectZxing(ev) {
        this.state.selectedCamera = ev.target.value;
        await this.startZxingScanner();
    }

    clearZxingVideoElement() {
        let videoElement = this.videoElementContainer.el.queryElementById("video-element");
        if (videoElement) {
            videoElement.remove();
        }
    }

    createZxingVideoElement() {
        let videoElement = document.createElement("video");
        video.setAttribute("id", "video-element");
        videoElement.style.width = "250px";
        videoElement.style.height = "250px";
        video.setAttribute("muted", "true");
        video.playsInline = "true";
        video.autoplay="true";
        this.videoElementContainer.el.appendChild(videoElement);
    }

    async startZxingScanner() {
        if (!this.zxingDetector) {
            this.props.onError(new Error(_t("ZXing detector not initialized.")));
            return;
        }

        try {
            this.zxingStream = await browser.navigator.mediaDevices.getUserMedia({
                audio: !1,
                video: {
                    deviceId: {
                        exact: this.state.selectedCamera
                        || this.state.availableCameras[0].deviceId
                    }
                }

            })
        } catch (err) {
            const errors = { /* ... as before ... */ };
            const errorMessage = _t("Could not start ZXing scanning. %(message)s", {
                message: errors[err.name] || err.message || "Unknown camera error.",
            });
            this.props.onError(new Error(errorMessage));
            return;
        }

        if (!this.videoPreviewRef.el) {
            await delay(50); // Wait a tick
            if (!this.videoPreviewRef.el) {
                this.stopZxingScanner();
                const errorMessage = _t("ZXing Barcode Video Scanner <video> element not found.");
                this.props.onError(new Error(errorMessage));
                return;
            }
        }

        this.videoPreviewRef.el.srcObject = this.zxingStream;
        await this.isZxingVideoReady();

        const { height, width } = getComputedStyle(this.videoPreviewRef.el);
        const divWidth = parseFloat(width);
        const divHeight = parseFloat(height);
        const tracks = this.zxingStream.getVideoTracks();
        if (tracks.length) {
            const [track] = tracks;
            const settings = track.getSettings();
            if (settings.width && settings.height) {
                 this.zxingZoomRatio = Math.min(divWidth / settings.width, divHeight / settings.height);
            } else {
                this.zxingZoomRatio = 1;
            }
        }
        this.zxingDetectorTimeout = setTimeout(this.detectZxingCode.bind(this), 100);
    }

    async toggleHtml5Scanner() {
        this.state.openCamera = !this.state.openCamera;
        if (this.state.openCamera) {
            await this.stopHtml5Scanner();
        } else {
            await this.startHtml5Scanner();
        }
    }

    stopZxingScanner() {
        clearTimeout(this.zxingDetectorTimeout);
        this.zxingDetectorTimeout = null;
        if (this.zxingStream) {
            this.zxingStream.getTracks().forEach((track) => track.stop());
            this.zxingStream = null;
        }
        this.state.isZxingReady = false;
    }

    async isZxingVideoReady() {
        if (!this.videoPreviewRef.el) return;
        while (!isZxingVideoElementReady(this.videoPreviewRef.el)) {
            await delay(10);
        }
        this.state.isZxingReady = true;
    }

    async detectZxingCode() {
        if (!this.zxingStream || !this.state.isZxingReady || this.zxingScanPaused || !this.videoPreviewRef.el || !this.zxingDetector) {
            if (this.zxingStream && this.zxingDetector) {
                 this.zxingDetectorTimeout = setTimeout(this.detectZxingCode.bind(this), this.props.delayBetweenScan);
            }
            return;
        }
        // ... (rest of detectZxingCode, zxingBarcodeDetected, isZXingBarcodeDetectorPolyfill, onResize, adaptZxingValuesWithRatio as before)
        let barcodeDetected = false;
        try {
            const codes = await this.zxingDetector.detect(this.videoPreviewRef.el);
            for (const code of codes) {
                if (
                    !this.isZXingBarcodeDetectorPolyfill() &&
                    this.zxingOverlayInfo.x !== undefined
                ) {
                    const { x, y, width, height } = this.adaptZxingValuesWithRatio(code.boundingBox);
                    if (
                        x < this.zxingOverlayInfo.x ||
                        x + width > this.zxingOverlayInfo.x + this.zxingOverlayInfo.width ||
                        y < this.zxingOverlayInfo.y ||
                        y + height > this.zxingOverlayInfo.y + this.zxingOverlayInfo.height
                    ) {
                        continue;
                    }
                }
                barcodeDetected = true;
                this.zxingBarcodeDetected(code.rawValue);
                break;
            }
        } catch (err) {
            console.error("Error during ZXing/Native code detection:", err);
        }

        if (this.zxingStream && !this.zxingScanPaused) {
            this.zxingDetectorTimeout = setTimeout(this.detectZxingCode.bind(this), barcodeDetected ? this.props.delayBetweenScan : 100);
        }
    }

    zxingBarcodeDetected(barcode) {
        this.props.onResult(barcode);
        if (this.props.delayBetweenScan > 0) {
            this.zxingScanPaused = true;
            clearTimeout(this.zxingDetectorTimeout);
            this.zxingDetectorTimeout = setTimeout(() => {
                this.zxingScanPaused = false;
                if (this.zxingStream) {
                    this.zxingDetectorTimeout = setTimeout(this.detectZxingCode.bind(this), 100);
                }
            }, this.props.delayBetweenScan);
        }
    }

    isZXingBarcodeDetectorPolyfill() {
        return this.zxingDetector && this.zxingDetector.__proto__.constructor.name === "ZXingBarcodeDetector";
    }

    onResize(overlayInfo) {
        this.zxingOverlayInfo = overlayInfo;
        if (this.zxingDetector && this.isZXingBarcodeDetectorPolyfill()) {
            this.zxingDetector.setCropArea(this.adaptZxingValuesWithRatio(this.zxingOverlayInfo, true));
        }
    }
    adaptZxingValuesWithRatio(domRect, dividerRatio = false) {
        const newObject = pick(domRect, "x", "y", "width", "height");
        for (const key of Object.keys(newObject)) {
            if (dividerRatio) {
                newObject[key] /= this.zxingZoomRatio;
            } else {
                newObject[key] *= this.zxingZoomRatio;
            }
        }
        return newObject;
    }
}

export function isBarcodeScannerSupported() { // This now checks generic media device support
    return Boolean(browser.navigator.mediaDevices && browser.navigator.mediaDevices.getUserMedia);
}