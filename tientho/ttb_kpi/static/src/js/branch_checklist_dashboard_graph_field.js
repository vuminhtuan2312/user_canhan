/** @odoo-module **/

import { registry } from "@web/core/registry";
import { JournalDashboardGraphField } from "@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field";

export class BranchChecklistDashboardGraphField extends JournalDashboardGraphField {
    getBarChartConfig() {
        const data = [];
        const labels = [];
        const backgroundColor = [];

        // Mặc định data[0] là object chứa key và values
        this.data[0].values.forEach((item) => {
            data.push(item.value);
            labels.push(item.label);
            // Gán màu theo label checklist
            if (item.label === "Cần duyệt") {
                backgroundColor.push("#85586F"); // tím
            } else if (item.label === "Nghiệm thu") {
                backgroundColor.push("#2C3E50"); // xanh đậm
            } else if (item.label === "Trễ hạn") {
                backgroundColor.push("#BCAAA4"); // vàng nhạt
            } else {
                backgroundColor.push("#CCCCCC"); // Mặc định
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

export const branchChecklistDashboardGraphField = {
    component: BranchChecklistDashboardGraphField,
    supportedTypes: ["text"],
    extractProps: ({ attrs }) => ({
        graphType: attrs.graph_type,
    }),
};

registry.category("fields").add("branch_dashboard_graph_check_list", branchChecklistDashboardGraphField);