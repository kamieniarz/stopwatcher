import time
import requests
import argparse
import json

from pymysql import connect

try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

DEFAULT_CONFIG = "default.ini"

### Queries
QUERY_DROP = """DROP TABLE {db_extra_dbname}.{db_extra};"""
QUERY_CREATE_EXTRA = """CREATE TABLE IF NOT EXISTS {db_extra_dbname}.{db_extra} SELECT * FROM {db_dbname}.{db_origin};"""
QUERY_CHECK = """SELECT {db_id}, {db_lat}, {db_lon}, {db_name}, {db_img} FROM {db_dbname}.{db_table}
WHERE (
    {db_lat} >= {lat_small} AND {db_lat} <= {lat_big}
  AND
    {db_lon} >= {lon_small} AND {db_lon} <= {lon_big}
)
"""
QUERY_CHECK_ORIGIN = """SELECT {db_lat}, {db_lon}, {db_name}, {db_img} FROM {db_dbname}.{db_table}
WHERE (
    {db_id} = '{db_extra_id}'
)
"""
QUERY_CHECK_DELETED = """SELECT {db_name}, {db_img}, {db_id} FROM {db_dbname}.{db_table}
WHERE {db_updated} < UNIX_TIMESTAMP() - {limit}
AND
(
    {db_lat} >= {lat_small} AND {db_lat} <= {lat_big}
  AND
    {db_lon} >= {lon_small} AND {db_lon} <= {lon_big}
)
"""
QUERY_EXIST_TABLE = """SHOW TABLES LIKE '{db_extra_table}'
"""
QUERY_CHECK_UPDATE = """select *, count(external_id) from ingress_portals where updated < UNIX_TIMESTAMP() - 86400; 
"""

def create_config(config_path):
    config = dict()
    config_raw = ConfigParser()
    config_raw.read(DEFAULT_CONFIG)
    config_raw.read(config_path)
    ### Config
    config['docheck'] = config_raw.getboolean(
        'Edit Watcher',
        'ENABLE')
    config['db_extra_dbname'] = config_raw.get(
        'Edit Watcher',
        'EXTRA_PORTAL_DB_NAME')
    config['db_extra_table'] = config_raw.get(
        'Edit Watcher',
        'EXTRA_PORTAL_TABLE')
    config['webhook'] = config_raw.get(
        'Edit Watcher',
        'WEBHOOK_URL')
    config['embed_image'] = config_raw.get(
        'Edit Watcher',
        'IMAGE')
    config['deleted_maxcount'] = config_raw.getint(
        'Edit Watcher',
        'DELETED_LIMIT')
    config['deleted_maxtime'] = config_raw.get(
        'Edit Watcher',
        'DELETED_TIMESPAN')
    config['language'] = config_raw.get(
        'Config',
        'LANGUAGE')

    config['bbox'] = config_raw.get(
        'Config',
        'BBOX')
    config['bbox'] = list(config['bbox'].split(','))

    config['db_scan_schema'] = config_raw.get(
        'DB',
        'SCANNER_DB_SCHEMA')
    config['db_portal_schema'] = config_raw.get(
        'DB',
        'PORTAL_DB_SCHEMA')
    config['db_host'] = config_raw.get(
        'DB',
        'HOST')
    config['db_port'] = config_raw.getint(
        'DB',
        'PORT')
    config['db_user'] = config_raw.get(
        'DB',
        'USER')
    config['db_pass'] = config_raw.get(
        'DB',
        'PASSWORD')
    config['db_portal_dbname'] = config_raw.get(
        'DB',
        'PORTAL_DB_NAME')

    return config

def connect_db(config):
    mydb = connect(
        host=config['db_host'],
        user=config['db_user'],
        passwd=config['db_pass'],
        database=config['db_extra_dbname'],
        port=config['db_port'],
        autocommit=True)

    return mydb

def db_config(config):
    if config['db_portal_schema'] == "pmsf":
        config['db_portal_table'] = "ingress_portals"
        config['db_portal_id'] = "external_id"
        config['db_portal_lat'] = "lat"
        config['db_portal_lon'] = "lon"
        config['db_portal_name'] = "name"
        config['db_portal_img'] = "url"
        config['db_portal_updated'] = "updated"

    config['db_extra_id'] = config['db_portal_id']
    config['db_extra_lat'] = config['db_portal_lat']
    config['db_extra_lon'] = config['db_portal_lon']
    config['db_extra_name'] = config['db_portal_name']
    config['db_extra_img'] = config['db_portal_img']

def get_deleted():
    return open("txt/deleted.txt", "r").read().splitlines()

def send_webhook_location(config, db_portal_img, db_portal_name, db_portal_lat, db_portal_lon, db_extra_lat, db_extra_lon):
    embed_desc = (locale['from'] + " `" + str(db_extra_lat) + "," + str(db_extra_lon) + "`\n" + locale['to'] + " `" + str(db_portal_lat) + "," + str(db_portal_lon) + "`\n\n[Google Maps](https://www.google.com/maps/search/?api=1&query=" + str(db_portal_lat) + "," + str(db_portal_lon) + ") | [Intel](https://intel.ingress.com/intel?ll=" + str(db_portal_lat) + "," + str(db_portal_lon) + "&z=18&pll=" + str(db_portal_lat) + "," + str(db_portal_lon) + ")")
    embed_title = (db_portal_name + " " + locale['location_edit_title'])
    data = {
        "username": locale['edit_title'],
        "avatar_url": config['embed_image'],
        "embeds": [{
            "title": embed_title,
            "description": embed_desc,
            "thumbnail": {
                "url": db_portal_img
            },
        }]
    }
    webhooks = json.loads(config['webhook'])
    for webhook in webhooks:
        result = requests.post(webhook, json=data)
        print(result)

def send_webhook_title(config, db_portal_img, db_portal_name, db_extra_name, db_portal_lat, db_portal_lon):
    embed_desc = (locale['from'] + " `" + db_extra_name + "`\n" + locale['to'] + " `" + db_portal_name + "`\n\n[Google Maps](https://www.google.com/maps/search/?api=1&query=" + str(db_portal_lat) + "," + str(db_portal_lon) + ") | [Intel](https://intel.ingress.com/intel?ll=" + str(db_portal_lat) + "," + str(db_portal_lon) + "&z=18&pll=" + str(db_portal_lat) + "," + str(db_portal_lon) + ")")
    embed_title = (db_extra_name + " " + locale['title_edit_title'])
    data = {
        "username": locale['edit_title'],
        "avatar_url": config['embed_image'],
        "embeds": [{
            "title": embed_title,
            "description": embed_desc,
            "thumbnail": {
                "url": db_portal_img
            },
        }]
    }
    webhooks = json.loads(config['webhook'])
    for webhook in webhooks:
        result = requests.post(webhook, json=data)
        print(result)

def send_webhook_image(config, db_portal_img, db_portal_name, db_extra_img, db_portal_lat, db_portal_lon):
    embed_desc = (locale['from'] + " [Link](" + db_extra_img + ")\n" + locale['to'] + " [Link](" + db_portal_img + ")\n\n[Google Maps](https://www.google.com/maps/search/?api=1&query=" + str(db_portal_lat) + "," + str(db_portal_lon) + ") | [Intel](https://intel.ingress.com/intel?ll=" + str(db_portal_lat) + "," + str(db_portal_lon) + "&z=18&pll=" + str(db_portal_lat) + "," + str(db_portal_lon) + ")")
    embed_title = (db_portal_name + " " + locale['image_edit_title'])
    data = {
        "username": locale['edit_title'],
        "avatar_url": config['embed_image'],
        "embeds": [{
            "title": embed_title,
            "description": embed_desc,
            "thumbnail": {
                "url": db_portal_img
            },
        }]
    }
    webhooks = json.loads(config['webhook'])
    for webhook in webhooks:
        result = requests.post(webhook, json=data)
        print(result)

def check_edits(config):
    query_extra_create = QUERY_CREATE_EXTRA.format(
        db_extra_dbname=config['db_extra_dbname'],
        db_extra=config['db_extra_table'],
        db_dbname=config['db_portal_dbname'],
        db_origin=config['db_portal_table']
    )

    query_extra_exist = QUERY_EXIST_TABLE.format(
        db_extra_table=config['db_extra_table']
    )
    cursor.execute(query_extra_exist)
    result_exist_table = cursor.fetchone()

    if result_exist_table:
        print("Found an existing extra table. Looking for edits now")
    else:
        print("Found no extra table, creating one now. You can now safely set this script up to run every now and then.")
        cursor.execute(query_extra_create)

    check_extra_query = QUERY_CHECK.format(
        db_id=config['db_extra_id'],
        db_lat=config['db_extra_lat'],
        db_lon=config['db_extra_lon'],
        db_name=config['db_extra_name'],
        db_img=config['db_extra_img'],
        db_dbname=config['db_extra_dbname'],
        db_table=config['db_extra_table'],
        lat_small=config['bbox'][1],
        lat_big=config['bbox'][3],
        lon_small=config['bbox'][0],
        lon_big=config['bbox'][2]
    )
    cursor.execute(check_extra_query)
    result_extra = cursor.fetchall()

    for db_extra_id, db_extra_lat, db_extra_lon, db_extra_name, db_extra_img in result_extra:
        check_origin_query = QUERY_CHECK_ORIGIN.format(
            db_id=config['db_portal_id'],
            db_lat=config['db_portal_lat'],
            db_lon=config['db_portal_lon'],
            db_name=config['db_portal_name'],
            db_img=config['db_portal_img'],
            db_dbname=config['db_portal_dbname'],
            db_table=config['db_portal_table'],
            db_extra_id=db_extra_id
        )
        cursor.execute(check_origin_query)
        result_origin = cursor.fetchall()

        for db_portal_lat, db_portal_lon, db_portal_name, db_portal_img in result_origin:
            if not db_extra_lat == db_portal_lat or not db_extra_lon == db_portal_lon:
                print(db_portal_name + " was moved. Sending a Webhook for it.")
                send_webhook_location(config, db_portal_img, db_portal_name, db_portal_lat, db_portal_lon, db_extra_lat, db_extra_lon)
            if not db_extra_name == db_portal_name:
                print(db_portal_name + " got another name. Sending a Webhook for it.")
                send_webhook_title(config, db_portal_img, db_portal_name, db_extra_name, db_portal_lat, db_portal_lon)
            if not db_extra_img == db_portal_img:
                print(db_portal_name + " got another image. Sending a Webhook for it.")
                send_webhook_image(config, db_portal_img, db_portal_name, db_extra_img, db_portal_lat, db_portal_lon)

    check_deleted_query = QUERY_CHECK_DELETED.format(
        db_lat=config['db_portal_lat'],
        db_lon=config['db_portal_lon'],
        db_img=config['db_portal_img'],
        db_id=config['db_portal_id'],
        db_updated=config['db_portal_updated'],
        db_name=config['db_portal_name'],
        limit=config['deleted_maxtime'],
        db_dbname=config['db_portal_dbname'],
        db_table=config['db_portal_table'],
        lat_small=config['bbox'][1],
        lat_big=config['bbox'][3],
        lon_small=config['bbox'][0],
        lon_big=config['bbox'][2]
    )
    cursor.execute(check_deleted_query)
    result_deleted = cursor.fetchall()

    if len(result_deleted) <= config['deleted_maxcount']:
        for db_portal_name, db_portal_img, db_portal_id in result_deleted:
            if not db_portal_id in get_deleted():
                print("Found possible deleted Portal: " + db_portal_name)
                embed_desc = ("[Google Maps](https://www.google.com/maps/search/?api=1&query=" + str(db_portal_lat) + "," + str(db_portal_lon) + ") | [Intel](https://intel.ingress.com/intel?ll=" + str(db_portal_lat) + "," + str(db_portal_lon) + "&z=18)")
                embed_title = (db_portal_name + " " + locale['deleted_title'])
                data = {
                    "username": locale['edit_title'],
                    "avatar_url": config['embed_image'],
                    "embeds": [{
                        "title": embed_title,
                        "description": embed_desc,
                        "thumbnail": {
                            "url": db_portal_img
                        },
                    }]
                }
                webhooks = json.loads(config['webhook'])
                for webhook in webhooks:
                    result = requests.post(webhook, json=data)
                    print(result)
                with open("txt/deleted.txt", "a") as f:
                    f.write(db_portal_id + "\n")
    else:
        print("Found " + str(len(result_deleted)) + " possible deleted Portals. Not going to send Webhooks for that. Please review your Scraper Cookie, Configs and Database!")
        print("Portal ID   |   Portal Name")
        for db_portal_name, db_portal_img, db_portal_id in result_deleted:
            print(db_portal_id + "   |   " + db_portal_name)

    query_extra_drop = QUERY_DROP.format(
        db_extra_dbname=config['db_extra_dbname'],
        db_extra=config['db_extra_table']
    )
    cursor.execute(query_extra_drop)

    cursor.execute(query_extra_create)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config", default="default.ini", help="Config file to use")
    args = parser.parse_args()
    config_path = args.config
    config = create_config(config_path)

    mydb = connect_db(config)
    cursor = mydb.cursor()
    db_config(config)

    with open(f"locale/{config['language']}.json") as localejson:
        locale = json.load(localejson)

    if config['docheck']:
        check_edits(config)
    else:
        print("Edit checking disabled!")

    cursor.close()
    mydb.close()