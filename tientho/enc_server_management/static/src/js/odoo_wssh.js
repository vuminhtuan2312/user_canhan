odoo.define('odoo_wssh', function (require) {

    var FormController = require('web.FormController');
    var FormRenderer = require('web.FormRenderer');

    FormRenderer.include({
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            this.iframeWin = false
            this.iframeWinID = false
        },
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._reconnectWSSH()
            });
        },

        _reconnectWSSH: function () {
            var self = this;
            var record = self.state;
            if (record.model !== 'action.update') {
                return
            }
            if (self.iframeWin && self.iframeWinID === record.res_id) {
                return
            }
            setTimeout(function () {
                var iframe = document.getElementById('webssh');
                var iframeWin = iframe.contentWindow || iframe;
                var iframeDoc = iframe.contentDocument || iframeWin.document;
                $(iframeDoc).ready(function (event) {
                    self.iframe = document.getElementById('webssh');
                    self._connectWSSH()
                });
            }, 100)
        },

        _connectWSSH: function () {
            var self = this;
            const record = self.state;
            self._rpc({
                model: record.model,
                method: 'get_wssh_opts',
                args: [record.res_id],
            }).then(function (opts) {
                var iframe = self.iframe
                var iframeWin = iframe.contentWindow || iframe;
                iframeWin.wssh.connect(opts)
            }).then(function () {
                setTimeout(function () {
                    self._getIframeWin()
                }, 1000)
            });
        },

        _getIframeWin: function () {
            var self = this;
            var iframe = self.iframe
            var iframeWin = iframe.contentWindow || iframe;
            var iframeDoc = iframe.contentDocument || iframeWin.document;
            const record = self.state;
            if (iframeDoc.getElementById('terminal').children.length) {
                self.iframeWin = iframeWin
                self.iframeWinID = record.res_id
            }
        },
    });

    FormController.include({
        update: async function () {
            await this._super(...arguments);
            this.renderer._reconnectWSSH()
        },

        _runWebSSHCommand: function (name) {
            var self = this;
            var record = self.model.get(self.handle);
            var iframeWin = self.renderer.iframeWin
            iframeWin.wssh.send('clear')
            self.renderer._rpc({
                model: self.modelName,
                method: name,
                args: [record.res_id],
            }).then (function (command) {
                iframeWin.wssh.send(command)
            });
        },

        _onButtonClicked: function (ev) {
            var self = this;
            var attrs = ev.data.attrs;
            if (attrs.type === 'wssh'){
                if (!self.renderer.iframeWin) {
                    var title = 'Lỗi';
                    var mes = 'Lỗi khi chạy lệnh!\nVui lòng tải lại trang.';
                    self.do_notify(title, mes, false);
                    return
                }

                ev.stopPropagation();

                this._disableButtons();

                self.saveRecord(self.handle, {
                    stayInEdit: true,
                }).then(function () {
                    self._runWebSSHCommand(attrs.name)
                    self._enableButtons();
                    if (attrs.close) {
                        self.trigger_up('close_dialog');
                    }
                }).guardedCatch(this._enableButtons.bind(this));

            } else {
                this._super.apply(this, arguments);
            }
        },
    });


});