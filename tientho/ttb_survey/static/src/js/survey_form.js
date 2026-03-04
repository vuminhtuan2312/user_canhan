/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import {
    deserializeDate,
    deserializeDateTime,
    parseDateTime,
    parseDate,
    serializeDateTime,
    serializeDate,
} from "@web/core/l10n/dates";

publicWidget.registry.SurveyFormWidget.include({

    // override function
    _onRadioChoiceClick: function (event) {
        this._super(arguments)
        var $target = $(event.currentTarget);
        if ($target.next().text().trim().toLowerCase() === 'không đạt') {
            if ($target.closest('div').nextAll('div').has('input[type="file"]').first()) {
                $target.closest('div').nextAll('div').has('input[type="file"]').first().removeClass("d-none")
            }
        }
        if ($target.next().text().trim().toLowerCase() === 'đạt') {
            if ($target.closest('div').nextAll('div').has('input[type="file"]').first()) {
                $target.closest('div').nextAll('div').has('input[type="file"]').first().addClass("d-none")
            }
        }

    },
    _submitForm: async function (options) {
        var params = {};
        if (options.previousPageId) {
            params.previous_page_id = options.previousPageId;
        }
        if (options.nextSkipped) {
            params.next_skipped_page_or_question = true;
        }
        var route = "/survey/submit";

        if (this.options.isStartScreen) {
            route = "/survey/begin";
            // Hide survey title in 'page_per_question' layout: it takes too much space
            if (this.options.questionsLayout === 'page_per_question') {
                this.$('.o_survey_main_title').fadeOut(400);
            }
        } else {
            var $form = this.$('form');
            var formData = new FormData($form[0]);

            if (!options.skipValidation) {
                // Validation pre submit
                if (!this._validateForm($form, formData)) {
                    return;
                }
            }

            await this._prepareSubmitValues(formData, params);
        }

        // prevent user from submitting more times using enter key
        this.preventEnterSubmit = true;

        if (this.options.sessionInProgress) {
            // reset the fadeInOutDelay when attendee is submitting form
            this.fadeInOutDelay = 400;
            // prevent user from clicking on matrix options when form is submitted
            this.readonly = true;
        }

        const submitPromise = rpc(
            `${route}/${this.options.surveyToken}/${this.options.answerToken}`,
            params
        );

        if (!this.options.isStartScreen && this.options.scoringType == 'scoring_with_answers_after_page') {
            const [correctAnswers] = await submitPromise;
            if (Object.keys(correctAnswers).length && document.querySelector('.js_question-wrapper')) {
                this._showCorrectAnswers(correctAnswers, submitPromise, options);
                return;
            }
        }
        this._nextScreen(submitPromise, options);
    },

    _prepareSubmitValues: async function (formData, params) {
        var self = this;
        formData.forEach(function (value, key) {
            switch (key) {
                case 'csrf_token':
                case 'token':
                case 'page_id':
                case 'question_id':
                    params[key] = value;
                    break;
            }
        });

        const questionElements = this.$('[data-question-type]').toArray();

        for (const el of questionElements) {
            const $el = $(el);
            const type = $el.data('questionType');

            switch (type) {
                case 'text_box':
                case 'char_box':
                case 'numerical_box':
                    params[el.name] = el.value;
                    break;

                case 'date':
                case 'datetime': {
                    const [parse, serialize] =
                        type === 'date'
                            ? [parseDate, serializeDate]
                            : [parseDateTime, serializeDateTime];
                    const date = parse(el.value);
                    params[el.name] = date ? serialize(date) : '';
                    break;
                }

                case 'scale':
                case 'simple_choice_radio':
                case 'multiple_choice':
                    // ✅ await here — this triggers image upload
                    params = await self._prepareSubmitChoices(params, $el, $el.data('name'));
                    break;

                case 'matrix':
                    params = self._prepareSubmitAnswersMatrix(params, $el);
                    break;
            }
        }
    },

    _prepareSubmitChoices: async function (params, $parent, questionId) {
        var self = this;
        $parent.find('input:checked').each(function () {
            if (this.value !== '-1') {
                params = self._prepareSubmitAnswer(params, questionId, this.value);
            }
        });
        params = self._prepareSubmitComment(params, $parent, questionId, false);
        params = await self._prepareSubmitImage(params, $parent, questionId, false);
        return params;
    },

     _fileToBase64: function(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.onload = () => resolve(reader.result.split(',')[1]);
                reader.onerror = reject;
            })
     },

     _prepareSubmitImage: async function(params, $parent, questionId, isMatrix) {
         var self = this;
         const inputs = $parent.find("input[class='form-control']");
         const value = {}
         for (const input of inputs) {
             if (input.files && input.files.length) {
                 const files = [];
                 for (const file of input.files) {
                     const result = await self._fileToBase64(file)
                     files.push(result)
                 }
                 value['files'] = files;
             }
             if (!isMatrix) {
                 params = self._prepareSubmitAnswer(params, questionId, value);
             }
         }
         return params;
     },
});

publicWidget.registry.SurveyFormExtend = publicWidget.Widget.extend({
    selector: '.o_survey_form',
    events: {
        'mouseenter span.toggle-description': '_onDescriptionHover',
        'mouseleave span.toggle-description': '_onDescriptionHover',
        'onchange div.upload-container': '_onImageUpload'
    },

    _onImageUpload: function(ev) {
        ev.preventDefault();
        var $target = $(ev.currentTarget);
        var $files = $target.files;
        for (const file of $files) {
            let $img = $("<img />")
            $img.attr('src', URL.createObjectURL(file))
            $img.appendTo($target);
        }
    },

    _onDescriptionHover: function(ev) {
        ev.preventDefault();
        var $icon = $(ev.currentTarget);
        var $parent = $icon.closest('div');
        var $description = $parent.find('div.text-muted.oe_no_empty.mt-1.text-break')
        if ($description.length) {
            $description.toggleClass("d-none");
        }
    }

})

export default publicWidget.registry.SurveyFormExtend;
