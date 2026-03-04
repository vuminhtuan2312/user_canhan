from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class AutoBackupConfig(models.Model):
    _name = 'auto.backup.config'
    _inherits = {'ir.cron': 'cron_id'}
    _description = "Cấu hình backup"

    server = fields.Many2one('server.data', string="Server", required=1)

    db_name = fields.Char('DBNAME', required=1)
    db_user = fields.Char('DBUSER', required=1)
    pg_pass = fields.Char('PGPASSWORD', required=1)
    data_dir = fields.Char('DATADIR', required=1)
    working_path = fields.Char('WORKINGPATH', required=1)
    upload_type = fields.Selection(selection=[('ftp', 'FTP server'), ('nextcloud', 'NextCloud server')], required=1, default='ftp')

    # FTP server
    ftp_host = fields.Many2one('ftp.host', string="FTP host")
    remote_path = fields.Char('REMOTEPATH')

    # Nextcloud server
    nextcloud_host = fields.Many2one('nextcloud.host', string="NextCloud host")
    nextcloud_path = fields.Char('NextCloud path')

    history_ids = fields.One2many('auto.backup.history', 'config_id', string="History")

    cron_id = fields.Many2one('ir.cron', 'Schedule', auto_join=True, index=True, ondelete="cascade", required=True)

    template_data = fields.Text('File sh')

    # model_id = fields.Many2one(default=lambda s: s.env['ir.model'].search([('name', '=', 'auto.backup.config')]))
    # code = fields.Text(string='Python Code', groups='base.group_system', default='model.action_backup()')

    @api.model
    def default_get(self, fields_list):
        res = super(AutoBackupConfig, self).default_get(fields_list)
        res['model_id'] = self.env['ir.model'].search([('name', '=', 'auto.backup.config')])
        res['code'] = 'model.action_run_backup()'
        res['interval_type'] = 'days'
        # res['numbercall'] = -1
        return res

    @api.model
    def create(self, values):
        values['usage'] = 'ir_cron'
        rec = super(AutoBackupConfig, self).create(values)
        rec.code = f'model.browse({rec.id}).action_run_backup()'
        return rec

    def generator_backup_folder(self):
        ssh = self.server.ssh_connect()
        server = self.nextcloud_host.server
        dav_path = self.nextcloud_host.dav_path
        user = self.nextcloud_host.user
        password = self.nextcloud_host.password
        create_path = [server, dav_path, user]
        data = []
        for path in self.nextcloud_path.split('/')[1:]:
            create_path.append(path)
            command = f"curl -u {user}:{password} -X MKCOL {'/'.join(create_path)}"
            ssh.exec_command(command)
            stdin, stdout, stderr = ssh.exec_command(command)
            data.append(command)
            data.append(''.join(iter(stdout.readline, "")))
        ssh.close()
        return self.env['warning_box'].info(title='Success',
                                            message="\n".join(data))

    def generator_sh_backup_template(self):
        data_upload = ''
        if self.upload_type == 'ftp':
            data_upload = f"""
echo "starting tranfer to FTP {self.ftp_host.server}" && \\
error=$(ftp -n {self.ftp_host.server} {self.ftp_host.port} <<-EOF
binary
quote USER {self.ftp_host.user}
quote PASS {self.ftp_host.password}
cd {self.remote_path}
put $FILENAME".sql.zip"
put $FILENAME".zip"
quit
EOF
)

if [[ -n $error ]]; then
        echo "lỗi tranfer to FTP {self.ftp_host.server}: "$error
else
        echo "done tranfer to FTP {self.ftp_host.server}"
fi
"""
        if self.upload_type == 'nextcloud':
            server = self.nextcloud_host.server
            dav_path = self.nextcloud_host.dav_path
            user = self.nextcloud_host.user
            password = self.nextcloud_host.password
            nextcloud_path = self.nextcloud_path[1:]
            data_path = '/'.join([server, dav_path, user, nextcloud_path])
            data_upload = f"""
echo "starting tranfer to FTP {data_path}"
curl -u {user}:{password} -T $FILENAME".sql.zip" {data_path}"/"$FILENAME".sql.zip"
curl -u {user}:{password} -T $FILENAME".zip" {data_path}"/"$FILENAME".zip"
    """
        template = f"""
PGPASSWORD="{self.pg_pass}"
DBNAME="{self.db_name}"
DATADIR="{self.data_dir}"
DBUSER="{self.db_user}"

WORKINGPATH="{self.working_path}"
FILENAME=$DBNAME"_"$(date +"%Y_%m_%d_%H%M%S")

cd $WORKINGPATH"/"$DBNAME && \\
exec >>logfile.txt 2>&1 && \\
echo "-----------------------" && \\
echo "start backup database "$DBNAME" at "$(date +"%H:%M:%S %d/%m/%Y") && \\
echo "done cd backup folder." && \\
echo "starting backup sql "$DBNAME && \\
sudo PGPASSWORD=$PGPASSWORD pg_dump -U $DBUSER -d $DBNAME --no-owner | gzip -9 > $FILENAME".sql.zip" && \\
echo "done backup sql "$DBNAME && \\
echo "starting backup filestore from "$DATADIR"/"$DBNAME && \\
sudo zip -r $FILENAME".zip" $DATADIR"/"$DBNAME &>/dev/null && \\
echo "done backup filestore from "$DATADIR"/"$DBNAME && \\
{data_upload}

echo "cleanning data"
rm -f $FILENAME".sql.zip" $FILENAME".zip"
echo "done backup database "$DBNAME
"""
        self.template_data = template

    def generator_sh_backup_file(self):
        def mkdir(ssh, working_path, db_name, file_name):
            first_path = working_path.split('/')[1]
            sftp = ssh.open_sftp()
            if first_path != 'backup':
                try:
                    sftp.chdir(f"/{first_path}")
                except IOError:
                    raise UserError(f"Không thể tìm thấy thư mục /{first_path}.\n Vui lòng tạo thư mục /{first_path} hoặc chuyển sang thư mục /backup")
            path = f"{working_path}/{db_name}"
            command = f"mkdir -p {path}"
            ssh.exec_command(command)
            return path
        ssh = self.server.ssh_connect()
        file_name = f'{self.db_name}.sh'
        path = mkdir(ssh, self.working_path, self.db_name, file_name)
        if not self.template_data:
            self.generator_sh_backup_template()
        template = self.template_data
        template = template.split('\n')
        template = '\n'.join([f"echo '{x}' >> {file_name}" for x in template])
        command = f"""
cd {path}
echo '' > {file_name}
{template}
        """
        _logger.info(command)
        ssh.exec_command(command)
        ssh.close()

    def action_backup(self):
        self.action_run_backup()
        return self.env['warning_box'].info(title='Success', message="Action backup done!")

    def action_run_backup(self):
        def check_script_file(ssh, working_path, db_name, file_name):
            sftp = ssh.open_sftp()
            file = f"{working_path}/{db_name}/{file_name}"
            try:
                sftp.stat(file)
            except IOError:
                _logger.info(f"Không thể tìm thấy file {file}.\n Vui lòng thực hiện Tạo file script backup.")
            return file
        his = self.env['auto.backup.history'].create({
            'config_id': self.id,
            'state': 'new',
        })
        try:
            ssh = self.server.ssh_connect()
            file_name = f'{self.db_name}.sh'
            file = check_script_file(ssh, self.working_path, self.db_name, file_name)
            command = f"bash {file}"
            # self.server.run_command(ssh, command)
            ssh.exec_command(command, get_pty=True)
            # ssh.close()
            his.write({'state': 'done'})
        except Exception as e:
            _logger.info("Action backup failed %s.", self.name, exc_info=True)
            his.write({'state': 'fail'})

    def unlink(self):
        unlink_autobackup = self.env['auto.backup.config']
        unlink_cron = self.env['ir.cron']
        for backup in self:
            if not backup.exists():
                continue
            unlink_cron |= backup.cron_id
            unlink_autobackup |= backup
        res = super(AutoBackupConfig, unlink_autobackup).unlink()
        unlink_cron.unlink()
        self.clear_caches()
        return res


class AutoBackupHistory(models.Model):
    _name = 'auto.backup.history'
    _description = 'AutoBackupHistory'
    _rec_name = 'config_id'
    _order = 'create_date desc'

    config_id = fields.Many2one('auto.backup.config', 'Config')
    state = fields.Selection(
        [('new', 'Mới'),
         ('done', 'Hoàn thành'),
         ('fail', 'Lỗi')], string='Status')
