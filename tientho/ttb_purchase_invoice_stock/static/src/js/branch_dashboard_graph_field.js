/** @odoo-module **/

import { registry } from "@web/core/registry";
import { JournalDashboardGraphField } from "@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field";

export class BranchDashboardGraphField extends JournalDashboardGraphField {
    getBarChartConfig() {
        const data = [];
        const labels = [];
        const backgroundColor = [];

        // Mặc định data[0] là object chứa key và values
        this.data[0].values.forEach((item) => {
            data.push(item.value);
            labels.push(item.label);
            // Gán màu theo label
            if (item.label === "Khớp") {
                backgroundColor.push("#85586F"); // Xanh lá
            } else if (item.label === "Lệch tiền") {
                backgroundColor.push("#2C3E50"); // Đỏ
            } else if (item.label === "Lệch số lượng") {
                backgroundColor.push("#BCAAA4"); // Vàng
            } else {
                backgroundColor.push("#CCCCCC"); // Màu mặc định nếu có label khác
            }
        });

        return {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        backgroundColor,
                        data,
                        fill: "start",
                        label: this.data[0].key,
                    },
                ],
            },
            options: {
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        intersect: false,
                        position: "nearest",
                        caretSize: 0,
                    },
                },
                scales: {
                    y: {
                        display: false,
                    },
                    x: {
                        display: false,
                    },
                },
                maintainAspectRatio: false,
                elements: {
                    line: {
                        tension: 0.000001,
                    },
                },
            },
        };
    }
}

export const branchDashboardGraphField = {
    component: BranchDashboardGraphField,
    supportedTypes: ["text"],
    extractProps: ({ attrs }) => ({
        graphType: attrs.graph_type,
    }),
};

registry.category("fields").add("branch_dashboard_graph", branchDashboardGraphField);