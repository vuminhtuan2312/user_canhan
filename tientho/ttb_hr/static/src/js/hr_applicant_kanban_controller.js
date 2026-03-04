/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ApplicantKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    async sortRecordDrop(dataRecordId, dataGroupId, params) {
        const { element, parent, previous } = params;

        // Kiểm tra xem có phải đang di chuyển giữa các group không
        if (this.props.list.isGrouped && parent && parent.dataset.id !== element.parentElement.dataset.id) {
            let applicantId = null;

            // Tìm record tương ứng với dataRecordId
            const record = this.props.list.records.find(record => record.id === dataRecordId);
            if (record) {
                applicantId = record.resId; // Lấy ID thực từ resId
            }

            // Lấy stage ID từ target group
            let newStageId = null;

            // Tìm group tương ứng với parent element
            const targetGroup = this.props.list.groups.find(group => {
                // So sánh với group ID
                return group.id === parent.dataset.id;
            });

            if (targetGroup) {
                newStageId = targetGroup.value;
            }

            // Chỉ tiếp tục nếu có stage ID hợp lệ và khác với group hiện tại
            if (newStageId && newStageId !== dataGroupId) {
                try {
                    // Gọi server để quyết định có mở wizard hay không
                    const action = await this.orm.call(
                        "hr.applicant",
                        "open_change_stage_wizard",
                        [[applicantId], newStageId]
                    );

                    if (action) {
                        await this.actionService.doAction(action, {
                            onClose: async () => {
                                // Reset hover states bằng DOM selector global
                                this.resetGlobalDragStates();

                                // Reload data nếu component vẫn tồn tại
                                try {
                                    if (this.props?.list?.model) {
                                        await this.props.list.model.load();
                                        if (this.render && typeof this.render === 'function') {
                                            this.render(true);
                                        }
                                    }
                                } catch (error) {
                                    console.warn("Error reloading after wizard close:", error);
                                }
                            },
                        });
                        return; // Không thực hiện move mặc định
                    }
                } catch (error) {
                    console.error("Error opening wizard:", error);
                    // Reset states nếu có lỗi
                    this.resetGlobalDragStates();
                }
            }
        }

        // Nếu không có wizard hoặc không phải di chuyển group, thực hiện move mặc định
        return super.sortRecordDrop(dataRecordId, dataGroupId, params);
    }

    /**
     * Reset drag states toàn cục không phụ thuộc vào component instance
     * Phương pháp này an toàn vì không dựa vào this.el
     */
    resetGlobalDragStates() {
        // Sử dụng setTimeout để đảm bảo DOM đã ổn định
        setTimeout(() => {
            try {
                // Tìm tất cả kanban views trong document
                const kanbanViews = document.querySelectorAll('.o_kanban_view');

                kanbanViews.forEach(kanbanView => {
                    // Reset tất cả kanban groups
                    const kanbanGroups = kanbanView.querySelectorAll('.o_kanban_group');
                    kanbanGroups.forEach(group => {
                        // Loại bỏ các CSS classes hover/drag
                        const classesToRemove = [
                            'o_kanban_hover',
                            'o_kanban_drag_over',
                            'oe_kanban_global_click_edit',
                            'o_column_quick_create',
                            'ui-sortable-helper',
                            'ui-droppable-hover',
                            'ui-state-hover'
                        ];

                        classesToRemove.forEach(className => {
                            group.classList.remove(className);
                        });

                        // Reset inline styles
                        if (group.style.backgroundColor) {
                            group.style.removeProperty('background-color');
                        }
                        if (group.style.borderColor) {
                            group.style.removeProperty('border-color');
                        }
                    });

                    // Reset kanban headers
                    const kanbanHeaders = kanbanView.querySelectorAll('.o_kanban_group .o_kanban_header');
                    kanbanHeaders.forEach(header => {
                        header.classList.remove('o_kanban_hover', 'o_kanban_drag_over');
                    });

                    // Reset kanban records
                    const kanbanRecords = kanbanView.querySelectorAll('.o_kanban_record');
                    kanbanRecords.forEach(record => {
                        record.classList.remove('o_kanban_hover', 'o_kanban_drag_over', 'ui-dragging');
                    });
                });

                // Reset body classes
                const bodyClassesToRemove = [
                    'o_kanban_dragging',
                    'ui-sortable-helper',
                    'ui-dragging'
                ];

                bodyClassesToRemove.forEach(className => {
                    document.body.classList.remove(className);
                });

                // Reset cursor
                document.body.style.cursor = '';

                // Trigger mouseout events để reset :hover pseudo-classes
                const allHoverableElements = document.querySelectorAll('.o_kanban_group');
                allHoverableElements.forEach(element => {
                    try {
                        element.dispatchEvent(new MouseEvent('mouseout', {
                            bubbles: true,
                            cancelable: true
                        }));
                        element.dispatchEvent(new MouseEvent('mouseleave', {
                            bubbles: true,
                            cancelable: true
                        }));
                    } catch (e) {
                        // Ignore event errors
                    }
                });

            } catch (error) {
                console.warn("Error in resetGlobalDragStates:", error);
            }
        }, 150); // Delay 150ms để đảm bảo wizard đã đóng hoàn toàn
    }
}

registry.category("views").add("hr_applicant_kanban_with_wizard", {
    ...registry.category("views").get("kanban"),
    Renderer: ApplicantKanbanRenderer,
});
