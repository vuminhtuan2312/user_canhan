/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { deserializeDate, deserializeDateTime, formatDate, formatDateTime } from "@web/core/l10n/dates";

export class ManagerDashboard extends Component {
    static template = "ttb_khuvuichoi.ManagerDashboard";

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
                branch_ids: [],
            },
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
            shiftAssignments: [],
            employeeTasks: [],
            auditTasks: [],
            failedAuditTasks: [],
            postAuditsByArea: [],
            failedAuditLines: [],
            expandedAreas: {},
            expandedEmployees: {},
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

    async load() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("ttb.operational.task", "get_manager_dashboard_data", [], {
                range_key: this.state.rangeKey,
            });
            this.state.meta = data.meta || this.state.meta;
            this.state.counts = data.counts || this.state.counts;
            this.state.shiftAssignments = data.shift_assignments || [];
            this.state.employeeTasks = data.employee_tasks || [];
            this.state.auditTasks = data.audit_tasks || [];
            this.state.failedAuditTasks = data.failed_audit_tasks || [];
            this.state.postAuditsByArea = data.post_audits_by_area || [];
            this.state.failedAuditLines = data.failed_audit_lines || [];
            this.state.rangeLabel = data.range?.label || this.state.rangeLabel;
            this.state.rangeDomain = data.range?.domain || [];
            this.state.lastRefreshedAt = new Date();
            this._resetCountdown();
        } catch (e) {
            this.notification.add("Không thể tải dashboard quản lý. Vui lòng thử lại.", { type: "danger" });
            throw e;
        } finally {
            this.state.loading = false;
        }
    }

    setRange = async (rangeKey) => {
        this.state.rangeKey = rangeKey;
        await this.load();
    };

    toggleAutoRefresh = () => {
        this.state.autoRefreshEnabled = !this.state.autoRefreshEnabled;
        this._resetCountdown();
    };

    toggleAreaExpand(prefix, areaKey) {
        const key = `${prefix}_${areaKey}`;
        const current = this.state.expandedAreas[key];
        this.state.expandedAreas[key] = current === undefined ? true : !current;
    }

    isAreaExpanded(prefix, areaKey) {
        return Boolean(this.state.expandedAreas[`${prefix}_${areaKey}`]);
    }

    /** Trả về key string cho area (dùng trong template, tránh gọi String() trong OWL). */
    getAreaKey(val) {
        return val !== false && val != null ? String(val) : "none";
    }

    toggleEmployeeExpand(prefix, areaKey, employeeKey) {
        const key = `${prefix}_${areaKey}_${employeeKey}`;
        const current = this.state.expandedEmployees[key];
        this.state.expandedEmployees[key] = current === undefined ? true : !current;
    }

    isEmployeeExpanded(prefix, areaKey, employeeKey) {
        return Boolean(this.state.expandedEmployees[`${prefix}_${areaKey}_${employeeKey}`]);
    }

    _taskStatusRank(status) {
        const order = {
            suspended: 0, // Tạm hoãn
            ready: 1, // Sẵn sàng
            done: 2, // Hoàn thành
            undone: 3, // Chưa hoàn thành
            waiting: 4, // Chờ thực hiện
            delayed: 5, // Hoãn
        };
        return order[status] ?? 999;
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
        const ra = this._taskStatusRank(a?.status);
        const rb = this._taskStatusRank(b?.status);
        if (ra !== rb) return ra - rb;

        const ta = this._taskSortTimeMs(a);
        const tb = this._taskSortTimeMs(b);
        if (ta !== tb) return ta - tb;

        const na = (a?.name || "").toString();
        const nb = (b?.name || "").toString();
        return na.localeCompare(nb);
    }

    getEmployeeGroups(tasks, isDoneFn) {
        if (!tasks || !tasks.length) return [];
        const byEmp = {};
        for (const task of tasks) {
            const key = task.employee_id !== false && task.employee_id != null ? task.employee_id : "none";
            const name = task.employee_name || "Chưa giao";
            if (!byEmp[key]) {
                byEmp[key] = { employeeKey: key, employeeName: name, tasks: [], doneCount: 0 };
            }
            byEmp[key].tasks.push(task);
            if (isDoneFn(task)) byEmp[key].doneCount += 1;
        }
        return Object.values(byEmp).map((g) => ({
            ...g,
            tasks: [...g.tasks].sort((a, b) => this._compareTasksForDashboard(a, b)),
            total: g.tasks.length,
            percent: g.tasks.length ? Math.round((g.doneCount / g.tasks.length) * 10000) / 100 : 0,
        }));
    }

    getEmployeeGroupsForAreaEmployee(areaGroup) {
        return this.getEmployeeGroups(areaGroup.tasks, (t) => t.status === "done");
    }

    getEmployeeGroupsForAreaAudit(areaGroup) {
        return this.getEmployeeGroups(areaGroup.tasks, (t) => t.status === "pass");
    }

    getAreaGroups(tasks, isDoneFn) {
        if (!tasks || !tasks.length) return [];
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
            if (isDoneFn(task)) byArea[key].doneCount += 1;
        }
        return Object.values(byArea).map((g) => ({
            ...g,
            tasks: [...g.tasks].sort((a, b) => this._compareTasksForDashboard(a, b)),
            total: g.tasks.length,
            percent: g.tasks.length ? Math.round((g.doneCount / g.tasks.length) * 10000) / 100 : 0,
        }));
    }

    getAreaGroupsEmployee() {
        return this.getAreaGroups(this.state.employeeTasks, (t) => t.status === "done");
    }

    getAreaGroupsAudit() {
        return this.getAreaGroups(this.state.auditTasks, (t) => t.status === "pass");
    }

    getAreaGroupsFailed() {
        return this.getAreaGroups(this.state.failedAuditTasks || [], () => false);
    }

    getEmployeeGroupsForAreaFailed(areaGroup) {
        return this.getEmployeeGroups(areaGroup.tasks, () => false);
    }

    // Công việc không đạt (failedAuditLines): nhóm Cấp 1 = Khu vực, Cấp 2 = Nhân viên phụ trách
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

    getEmployeeGroupsForAreaFailedLines(areaGroup) {
        const byEmp = {};
        for (const line of areaGroup.lines) {
            const key = (line.employee_names || "").trim() || "none";
            if (!byEmp[key]) {
                byEmp[key] = { employeeKey: key, employeeName: line.employee_names || "Chưa giao", lines: [] };
            }
            byEmp[key].lines.push(line);
        }
        return Object.values(byEmp);
    }

    toggleAreaExpandFailed(areaKey) {
        const key = `fail_area_${areaKey}`;
        const current = this.state.expandedAreas[key];
        this.state.expandedAreas[key] = current === undefined ? true : !current;
    }

    isAreaExpandedFailed(areaKey) {
        return Boolean(this.state.expandedAreas[`fail_area_${areaKey}`]);
    }

    toggleEmployeeExpandFailed(areaKey, employeeKey) {
        const key = `fail_emp_${areaKey}_${employeeKey}`;
        const current = this.state.expandedEmployees[key];
        this.state.expandedEmployees[key] = current === undefined ? true : !current;
    }

    isEmployeeExpandedFailed(areaKey, employeeKey) {
        return Boolean(this.state.expandedEmployees[`fail_emp_${areaKey}_${employeeKey}`]);
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

    // Công việc của nhân viên: mở form Tất cả công việc (action_all_tasks_manager)
    openTask = async (id) => {
        const resId = Number(id);
        const action = await this.action.loadAction("ttb_khuvuichoi.action_all_tasks_manager");
        return this.action.doAction({ ...action, res_id: resId }, { viewType: "form", props: { resId } });
    };

    // Công việc hậu kiểm: mở form Hậu kiểm (action_audit)
    openTaskAudit = async (id) => {
        const resId = Number(id);
        const action = await this.action.loadAction("ttb_khuvuichoi.action_audit");
        return this.action.doAction({ ...action, res_id: resId }, { viewType: "form", props: { resId } });
    };

    // Phiếu phân công ca: mở form Phân công Ca
    openShiftAssignment = async (id) => {
        const resId = Number(id);
        const action = await this.action.loadAction("ttb_khuvuichoi.action_shift_assignments");
        return this.action.doAction({ ...action, res_id: resId }, { viewType: "form", props: { resId } });
    };

    // Phiếu hậu kiểm: mở form Phiếu hậu kiểm
    openPostAudit = async (id) => {
        const resId = Number(id);
        const action = await this.action.loadAction("ttb_khuvuichoi.action_ttb_post_audit");
        return this.action.doAction({ ...action, res_id: resId }, { viewType: "form", props: { resId } });
    };

    openReworkTask = async (id) => {
        if (!id) return;
        const resId = Number(id);
        const action = await this.action.loadAction("ttb_khuvuichoi.action_all_tasks_manager");
        return this.action.doAction({ ...action, res_id: resId }, { viewType: "form", props: { resId } });
    };

    // Mở danh sách task theo KPI: lọc theo cơ sở (branch_ids) do quản lý cơ sở phụ trách,
    // không dùng quản lý ca (assignment_id.manager_id).
    openTasksByKpi = async (kpiKey) => {
        const branchIds = this.state.meta?.branch_ids || [];
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
                    ["state", "in", ["waiting", "ready", "suspended", "delayed"]],
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
            ...(branchIds.length ? [["branch_id", "in", branchIds]] : []),
            ...rangeDomain,
            ...extraDomain,
        ];
        const searchDefaultFilter = {
            assigned: "dashboard_assigned",
            done: "dashboard_done",
            not_done: "dashboard_not_done",
            late: "dashboard_late",
        }[kpiKey] || "audit_pending";
        const action = await this.action.loadAction("ttb_khuvuichoi.action_all_tasks_manager");
        return this.action.doAction(
            {
                ...action,
                domain,
                context: {
                    [`search_default_${searchDefaultFilter}`]: 1,
                },
            },
            { target: "current" }
        );
    };

    formatPercent(value) {
        if (value == null || value === "") return "0,00";
        const num = Number(value);
        if (Number.isNaN(num)) return "0,00";
        return num.toFixed(2);
    }

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

    assignmentStateBadgeClass(state) {
        switch (state) {
            case "draft":
                return "text-bg-info";
            case "assigning":
                return "text-bg-warning";
            case "done":
                return "text-bg-success";
            case "cancel":
                return "text-bg-secondary";
            default:
                return "text-bg-light";
        }
    }

    statusBadgeClass(status) {
        // Chưa hoàn thành → đỏ; Hoãn / Tạm hoãn → vàng
        switch (status) {
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
            case "pending":
                return "text-bg-warning";
            case "pass":
                return "text-bg-success";
            case "fail":
                return "text-bg-danger";
            default:
                return "text-bg-light";
        }
    }

    taskRowClass(task) {
        if (task?.is_late) return "table-danger";
        if (task?.status === "delayed" || task?.status === "suspended") return "table-warning";
        return "";
    }

    getTaskCardBorderClass(task) {
        if (task?.is_late) return "border-danger";
        if (task?.status === "delayed" || task?.status === "suspended") return "border-warning";
        if (task?.status === "done") return "border-success";
        return "";
    }
}

registry.category("actions").add("ttb_manager_dashboard", ManagerDashboard);

