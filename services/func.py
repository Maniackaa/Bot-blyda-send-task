import json

from config_data.conf import BASE_DIR, get_my_loggers

logger, err_log = get_my_loggers()


data = {
    '5731181217': 'Мытищи',
    '6796213900': 'Видное',
    '1177005164': 'Владимир',
    '6386993630': 'Красногорск',
    '5432024787': 'Домодедово',
    '6304798277': 'Совхоз',
    '6983441538': 'Сколково',
    '6909172046': 'Павелецкая',
    '7148960993': 'Суханово',
}


def write_send_list_ids(data: dict):
    with open(BASE_DIR / 'send_list.txt', 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def read_send_list_ids() -> dict:
    logger.debug('Чтение списка рассылки')
    try:
        with open(BASE_DIR / 'send_list.txt', encoding='utf-8') as file:
            send_list_ids = json.load(file)
            logger.debug(f'Список прочитан:{send_list_ids}')
            return send_list_ids
    except Exception as err:
        logger.error(err)
        err_log.error(err, exc_info=True)


# write_send_list_ids({"6247356284": "TestJ"})
# write_send_list_ids(data)
x = read_send_list_ids()
print(x.keys())