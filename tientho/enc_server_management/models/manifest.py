# /opt/odoo13/venv/bin/python3 /opt/odoo13-test/odoo/odoo/abc.py > /opt/odoo13-test/odoo/odoo/abc.json
import release, json
import psycopg2
db_name = 'thanhlong'
db_user = 'odoo13'
db_password = 'xxxx'

def sql(query):
    """ Connect to the PostgreSQL database server """
    conn = None
    data = tuple()
    try:
        params = {
            'host': "localhost",
            'database': db_name,
            'user': db_user,
            'password': db_password
        }
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        cur.execute(query)
        data = cur.fetchall()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
        return data


def dump_db_manifest():
    a = sql('SHOW server_version_num')
    pg_version = "%d.%d" % divmod(int(a[0][0]) / 100, 100)
    data = sql("SELECT name, latest_version FROM ir_module_module WHERE state = 'installed'")
    modules = dict(data)
    manifest = {
        'odoo_dump': '1',
        'db_name': db_name,
        'version': release.version,
        'version_info': release.version_info,
        'major_version': release.major_version,
        'pg_version': pg_version,
        'modules': modules,
    }
    return manifest

jsons = json.dumps(dump_db_manifest(), indent=4)
print(jsons)

