odoo.define('run_command_result', function (require) {

    var core = require('web.core');
    var rpc = require('web.rpc');
    var FormController = require('web.FormController');

    function RunCommandResult(parent, params) {
        var data = params.params || '';
        var number = params.number || false;
        var id = params.id || false;
        ViewLogFile(data, number, id)
        if (!number) {
            var title = 'Success!';
            var mes = 'Run command successful!';
            FormController.do_notify(title, mes, false);
        }
    }

    function ViewLogFile(data, number, id) {
        var $code = $('.code');
        if($code.length > 0) {
            $code[0].innerText = data
        }
        if (id && number && $code.length > 0) {
            rpc.query({
                "model": 'action.update',
                "method": "action_view_log_file",
                "args": [id,number]
            }).then(function (result){
                if (result && result.length === 3) {
                   ViewLogFile(result[0], result[1], result[2]);
                }
            });
        }

    }

    core.action_registry.add("run_command_result", RunCommandResult);

    var FormRenderer = require('web.FormRenderer');
    FormRenderer.include({
        getLocalState: function () {
            var state = this._super.apply(this, arguments);
            var $code = $('.code');
            if($code.length > 0){
                state['code'] = $code[0].innerText
            }
            return state
        },
        setLocalState: function (state) {
            var res = this._super.apply(this, arguments);
            var $code = $('.code');
            if($code.length > 0 && state['code']) {
                $code[0].innerText = state['code']
            }
            return res
        },
    });
});