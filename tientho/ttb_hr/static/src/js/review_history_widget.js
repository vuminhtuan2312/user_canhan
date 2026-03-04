/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class ReviewInfoWidget extends Component {
    static template = "ttb_hr.ReviewInfoWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        super.setup();
        this.testResultData = {};

        onWillStart(async () => {
            await this.loadTestResultData();
        });
    }

    async loadTestResultData() {
        const recordId = this.props.record.resId;
        if (recordId) {
            try {
                const result = await rpc('/web/dataset/call_kw/hr.applicant/read', {
                    model: 'hr.applicant',
                    method: 'read',
                    args: [[recordId]],
                    kwargs: {
                        fields: ['test_result_ids']
                    }
                });

                if (result && result[0] && result[0].test_result_ids) {
                    const testResults = await rpc('/web/dataset/call_kw/test.result/read', {
                        model: 'test.result',
                        method: 'read',
                        args: [result[0].test_result_ids],
                        kwargs: {
                            fields: ['stage_id', 'result', 'reviewer_id']
                        }
                    });

                    testResults.forEach(record => {
                        if (record.stage_id && record.result) {
                            this.testResultData[record.stage_id[0]] = {
                                result: record.result,
                                reviewer: record.reviewer_id ? record.reviewer_id[1] : 'Chưa có',
                                reviewerId: record.reviewer_id ? record.reviewer_id[0] : null
                            };
                        }
                    });
                }
            } catch (error) {
                console.error('Error loading test result data:', error);
            }
        }
    }

    get groupedReviews() {
        const reviewRecords = this.props.record.data.review_infor_ids.records;

        // Lọc các bản ghi tiêu chí đã được đánh giá
        const filteredRecords = reviewRecords.filter(
            (rec) => rec.data.is_pass
        );

        // Nhóm theo stage
        const grouped = filteredRecords.reduce((acc, record) => {
            const stageKey = record.data.stage_name ? record.data.stage_name[0] : "no_stage";
            const stageName = record.data.stage_name ? record.data.stage_name[1] : "Chưa có vòng";

            if (!acc[stageKey]) {
                acc[stageKey] = {
                    stageName: stageName,
                    reviews: [],
                    stageResult: this.testResultData[stageKey] || null
                };
            }

            acc[stageKey].reviews.push({
                id: record.id,
                name: record.data.name,
                content: record.data.content,
                is_pass: record.data.is_pass,
            });
            return acc;
        }, {});

        return Object.entries(grouped).map(([stageId, groupData]) => {
            groupData.reviews.sort((a, b) => {
                return b.is_pass.localeCompare(a.is_pass);
            });

            return {
                stageId,
                stageName: groupData.stageName,
                reviews: groupData.reviews,
                stageResult: groupData.stageResult,
            };
        });
    }
}

registry.category("fields").add("review_info_widget", {
    component: ReviewInfoWidget,
    supportedTypes: ["one2many"],
});
