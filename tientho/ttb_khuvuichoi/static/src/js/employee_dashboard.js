/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { deserializeDate, deserializeDateTime, formatDate, formatDateTime } from "@web/core/l10n/dates";

export class EmployeeDashboard extends Component {
    static template = "ttb_khuvuichoi.EmployeeDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            currentTimeVNDate: "",
            currentTimeVNTime: "",
            meta: {
                uid: null,
            },
            notificationEnabled: true,
            isAdmin: false,
            rangeKey: "today",
            rangeLabel: "Hôm nay",
            rangeDomain: [],
            autoRefreshEnabled: false,
            refreshEverySec: 5,
            nextRefreshInSec: 5,
            lastRefreshedAt: null,
            counts: {
                assigned: 0,
                done: 0,
                not_done: 0,
                late: 0,
            },
            tasks: [],
            failedAuditTasks: [],
            failedAuditLines: [],
            expandedAreas: {},
            expandedAreasFailed: {},
        });

        onWillStart(async () => {
            await this.load();
            this._updateVietnamClock();
        });
        onMounted(() => {
            this._startTickers();
            this._clockInterval = setInterval(() => this._updateVietnamClock(), 1000);
        });
        onWillUnmount(() => {
            this._stopTickers();
            if (this._clockInterval) {
                clearInterval(this._clockInterval);
                this._clockInterval = null;
            }
        });
    }

    /**
     * Cập nhật thời gian realtime theo giờ Việt Nam (UTC+7).
     */
    _updateVietnamClock() {
        const VN_OFFSET_MS = 7 * 60 * 60 * 1000;
        const now = new Date();
        const vnNow = new Date(now.getTime() + VN_OFFSET_MS);
        const dayNames = ["Chủ Nhật", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"];
        const d = vnNow.getUTCDate();
        const m = vnNow.getUTCMonth() + 1;
        const y = vnNow.getUTCFullYear();
        const h = vnNow.getUTCHours();
        const min = vnNow.getUTCMinutes();
        const sec = vnNow.getUTCSeconds();
        const dayOfWeek = dayNames[vnNow.getUTCDay()];
        this.state.currentTimeVNDate = `${dayOfWeek}, ${d}/${m}/${y}`;
        this.state.currentTimeVNTime = [h, min, sec].map((n) => String(n).padStart(2, "0")).join(":");
    }

    async load() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("ttb.operational.task", "get_employee_dashboard_data", [], {
                range_key: this.state.rangeKey,
            });
            this.state.meta = data.meta || this.state.meta;
            this.state.notificationEnabled = data.meta?.notification_enabled !== false;
            this.state.isAdmin = Boolean(data.meta?.is_admin);
            this.state.counts = data.counts || this.state.counts;
            this.state.tasks = data.tasks || [];
            this.state.failedAuditTasks = data.failed_audit_tasks || [];
            this.state.failedAuditLines = data.failed_audit_lines || [];
            this.state.rangeLabel = data.range?.label || this.state.rangeLabel;
            this.state.rangeDomain = data.range?.domain || [];
            this.state.lastRefreshedAt = new Date();
            this._resetCountdown();
        } catch (e) {
            this.notification.add("Không thể tải dashboard. Vui lòng thử lại.", { type: "danger" });
            throw e;
        } finally {
            this.state.loading = false;
        }
    }

    async reload() {
        await this.load();
    }

    setRange = async (rangeKey) => {
        this.state.rangeKey = rangeKey;
        await this.load();
    };

    toggleAutoRefresh = () => {
        this.state.autoRefreshEnabled = !this.state.autoRefreshEnabled;
        this._resetCountdown();
    };

    onNotificationSwitchClick = async () => {
        const enabled = !this.state.notificationEnabled;
        this.state.notificationEnabled = enabled;
        try {
            await this.orm.call("res.users", "set_ttb_notification_enabled", [enabled]);
        } catch (e) {
            this.state.notificationEnabled = !enabled;
            this.notification.add("Không thể lưu tùy chọn thông báo.", { type: "danger" });
        }
    };

    toggleAreaExpand(areaKey) {
        const current = this.state.expandedAreas[areaKey];
        this.state.expandedAreas[areaKey] = current === undefined ? true : !current;
    }

    isAreaExpanded(areaKey) {
        return Boolean(this.state.expandedAreas[areaKey]);
    }

    toggleAreaExpandFailed(areaKey) {
        const current = this.state.expandedAreasFailed[areaKey];
        this.state.expandedAreasFailed[areaKey] = current === undefined ? true : !current;
    }

    isAreaExpandedFailed(areaKey) {
        return Boolean(this.state.expandedAreasFailed[areaKey]);
    }

    _taskStateRank(state) {
        const order = {
            suspended: 0, // Tạm hoãn
            ready: 1, // Sẵn sàng
            done: 2, // Hoàn thành
            undone: 3, // Chưa hoàn thành
            waiting: 4, // Chờ thực hiện
            delayed: 5, // Hoãn
        };
        return order[state] ?? 999;
    }

    _taskSortTimeMs(task) {
        const dt = task?.actual_date_end || task?.planned_date_start || task?.planned_date_end;
        if (dt) {
            try {
                return deserializeDateTime(dt).getTime();
            } catch {
                // ignore
            }
        }
        const d = task?.assignment_date;
        if (d) {
            try {
                return deserializeDate(d).getTime();
            } catch {
                // ignore
            }
        }
        return Number.POSITIVE_INFINITY;
    }

    _compareTasksForDashboard(a, b) {
        const ra = this._taskStateRank(a?.state);
        const rb = this._taskStateRank(b?.state);
        if (ra !== rb) return ra - rb;

        const ta = this._taskSortTimeMs(a);
        const tb = this._taskSortTimeMs(b);
        if (ta !== tb) return ta - tb;

        const na = (a?.name || "").toString();
        const nb = (b?.name || "").toString();
        return na.localeCompare(nb);
    }

    getAreaGroupsFailed() {
        const tasks = this.state.failedAuditTasks || [];
        const byArea = {};
        for (const task of tasks) {
            const key = task.area_id !== false && task.area_id != null ? task.area_id : "none";
            if (!byArea[key]) {
                byArea[key] = {
                    areaKey: key,
                    areaName: task.area_name || "Chưa phân khu vực",
                    tasks: [],
                };
            }
            byArea[key].tasks.push(task);
        }
        return Object.values(byArea);
    }

    /** Nhóm dòng không đạt (failedAuditLines) theo Khu vực - Cấp 1 */
    getAreaGroupsFailedLines() {
        const lines = this.state.failedAuditLines || [];
        if (!lines.length) return [];
        const byArea = {};
        for (const line of lines) {
            const key = line.area_id !== false && line.area_id != null ? String(line.area_id) : "none";
            if (!byArea[key]) {
                byArea[key] = { areaKey: key, areaName: line.area_name || "Chưa phân khu vực", lines: [] };
            }
            byArea[key].lines.push(line);
        }
        return Object.values(byArea);
    }

    getAreaGroups() {
        const tasks = this.state.tasks || [];
        const byArea = {};
        for (const task of tasks) {
            const key = task.area_id !== false && task.area_id != null ? task.area_id : "none";
            if (!byArea[key]) {
                byArea[key] = {
                    areaKey: key,
                    areaName: task.area_name || "Chưa phân khu vực",
                    tasks: [],
                    doneCount: 0,
                };
            }
            byArea[key].tasks.push(task);
            if (task.state === "done") byArea[key].doneCount += 1;
        }
        return Object.values(byArea).map((g) => ({
            ...g,
            tasks: [...g.tasks].sort((a, b) => this._compareTasksForDashboard(a, b)),
            total: g.tasks.length,
            percent: g.tasks.length ? Math.round((g.doneCount / g.tasks.length) * 10000) / 100 : 0,
        }));
    }

    _resetCountdown() {
        this.state.nextRefreshInSec = this.state.refreshEverySec;
    }

    _startTickers() {
        this._ticker = setInterval(async () => {
            if (!this.state.autoRefreshEnabled) {
                return;
            }
            if (this.state.loading) {
                return;
            }
            this.state.nextRefreshInSec = Math.max(0, (this.state.nextRefreshInSec || 0) - 1);
            if (this.state.nextRefreshInSec <= 0) {
                try {
                    await this.load();
                } catch {
                    // ignore refresh errors, user still can reload manually
                    this._resetCountdown();
                }
            }
        }, 1000);
    }

    _stopTickers() {
        if (this._ticker) {
            clearInterval(this._ticker);
            this._ticker = null;
        }
    }

    openTask = async (id) => {
        const resId = Number(id);
        const action = await this.action.loadAction("ttb_khuvuichoi.action_my_tasks");
        return this.action.doAction({ ...action, res_id: resId }, { viewType: "form", props: { resId } });
    };

    openTaskAudit = async (id) => {
        const resId = Number(id);
        const action = await this.action.loadAction("ttb_khuvuichoi.action_audit");
        return this.action.doAction({ ...action, res_id: resId }, { viewType: "form", props: { resId } });
    };

    openPostAudit = async (id) => {
        const resId = Number(id);
        const action = await this.action.loadAction("ttb_khuvuichoi.action_ttb_post_audit");
        return this.action.doAction({ ...action, res_id: resId }, { viewType: "form", props: { resId } });
    };

    openTasksByKpi = async (kpiKey) => {
        const uid = this.state.meta?.uid;
        const rangeDomain = this.state.rangeDomain || [];

        let extraDomain = [];
        switch (kpiKey) {
            case "assigned":
                extraDomain = [["state", "!=", "cancel"]];
                break;
            case "done":
                extraDomain = [
                    ["state", "=", "done"],
                    ["state", "!=", "cancel"],
                ];
                break;
            case "not_done":
                extraDomain = [
                    ["state", "in", ["waiting", "ready", "delayed"]],
                    ["state", "!=", "cancel"],
                ];
                break;
            case "late":
                extraDomain = [
                    ["is_late", "=", true],
                    ["state", "!=", "done"],
                    ["state", "!=", "cancel"],
                ];
                break;
            default:
                extraDomain = [["state", "!=", "cancel"]];
        }

        const domain = [
            ...(uid ? [["employee_id.user_id", "=", uid]] : []),
            ...rangeDomain,
            ...extraDomain,
        ];
        const searchDefaultFilter = {
            assigned: "dashboard_assigned",
            done: "dashboard_done",
            not_done: "dashboard_not_done",
            late: "dashboard_late",
        }[kpiKey] || "my_tasks";
        const action = await this.action.loadAction("ttb_khuvuichoi.action_my_tasks");
        return this.action.doAction(
            {
                ...action,
                domain,
                context: {
                    ...(action.context || {}),
                    search_default_my_tasks: 1,
                    [`search_default_${searchDefaultFilter}`]: 1,
                },
            },
            { target: "current" }
        );
    };

    formatDate(dateStr) {
        if (!dateStr) {
            return "-";
        }
        try {
            return formatDate(deserializeDate(dateStr));
        } catch {
            return dateStr;
        }
    }

    formatDateTime(dateTimeStr) {
        if (!dateTimeStr) {
            return "-";
        }
        try {
            return formatDateTime(deserializeDateTime(dateTimeStr));
        } catch {
            return dateTimeStr;
        }
    }

    formatDateTimeRange(startStr, endStr) {
        const start = this.formatDateTime(startStr);
        const end = this.formatDateTime(endStr);
        if (start === "-" && end === "-") {
            return "-";
        }
        if (end === "-") {
            return start;
        }
        if (start === "-") {
            return end;
        }
        return `${start} - ${end}`;
    }

    formatExecutionTime(task) {
        if (task?.actual_date_end) {
            return this.formatDateTime(task.actual_date_end);
        }
        return this.formatDateTimeRange(task?.planned_date_start, task?.planned_date_end);
    }

    formatLastRefreshedAt() {
        if (!this.state.lastRefreshedAt) {
            return "-";
        }
        try {
            return this.state.lastRefreshedAt.toLocaleString();
        } catch {
            return String(this.state.lastRefreshedAt);
        }
    }

    getAvatarUrl() {
        const meta = this.state.meta || {};
        if (meta.employee_id) {
            return `/web/image/hr.employee/${meta.employee_id}/image_128`;
        }
        if (meta.uid) {
            return `/web/image/res.users/${meta.uid}/image_128`;
        }
        return null;
    }

    stateBadgeClass(state) {
        switch (state) {
            case "waiting":
                return "text-bg-secondary";
            case "ready":
                return "text-bg-info";
            case "delayed":
                return "text-bg-warning";
            case "suspended":
                return "text-bg-warning";
            case "undone":
                return "text-bg-danger";
            case "done":
                return "text-bg-success";
            case "cancel":
                return "text-bg-dark";
            default:
                return "text-bg-light";
        }
    }

    taskRowClass(task) {
        if (task?.is_late) return "table-danger";
        if (task?.state === "delayed" || task?.state === "suspended") return "table-warning";
        return "";
    }

    /** Class viền thẻ công việc (kanban) theo trễ hạn / trạng thái */
    getTaskCardBorderClass(task) {
        if (task?.is_late) return "border-danger";
        if (task?.state === "delayed" || task?.state === "suspended") return "border-warning";
        return "";
    }
}

registry.category("actions").add("ttb_employee_dashboard", EmployeeDashboard);

