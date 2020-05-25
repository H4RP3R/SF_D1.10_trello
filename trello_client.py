#!/usr/bin/env python
# encoding: utf-8

import os
import requests
import readline
import sys
import json
from termcolor import colored, cprint


BASE_URL = 'https://api.trello.com/1/{}'


class LessThanOneValueError(Exception):
    '''Raised when the input value is less than 1'''
    pass


def get_auth_params(message=None):
    clear_screen()
    if message is not None:
        cprint(message, 'red')
    key = input('Ваш API ключ: ')
    token = input('Теперь токен: ')
    return {'key': key, 'token': token}


def clear_screen():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')


def show_help():
    '''Prints out commands list'''
    clear_screen()
    print('Комманды:')
    cprint('tasks', 'green', end='')
    print('         - получить данные всех колонок на доске')
    cprint('create task', 'green', end='')
    print('   - создать задачу')
    cprint('create column', 'green', end='')
    print(' - создать колонку')
    cprint('move', 'green', end='')
    print('          - переместить задачу в другую колонку')
    cprint('exit', 'green', end='')
    print('          - выход')
    print()


def show_tasks(board_id, auth_params):
    clear_screen()
    column_data = requests.get(BASE_URL.format('boards') + '/' +
                               board_id + '/lists', params=auth_params).json()

    if len(column_data) < 1:
        print('Нет созданных колонок')
        return

    for column in column_data:
        task_data = requests.get(BASE_URL.format('lists') + '/' +
                                 column['id'] + '/cards', params=auth_params).json()
        cprint(f"{column['name']} [{len(task_data)}]", 'green', attrs=['reverse'])

        if not task_data:
            print('  ' + 'Нет задач!')
            continue
        for task in task_data:
            print('  ' + task['name'])
        print('_' * 60)


def check_connection(auth_params, board_id):
    '''Validates token, key and board ID. On success returns status code 200'''
    response = requests.get(BASE_URL.format('boards') + '/' + board_id, params=auth_params)
    return response.status_code


def save_user_data(auth_params, board_id):
    '''Saves key, token and board ID to the json file'''
    with open('user_data.json', 'w') as f:
        user_data = {'auth_params': auth_params, 'board_id': board_id}
        json.dump(user_data, f)


def create_task(board_id, auth_params):
    clear_screen()
    show_tasks(board_id, auth_params)
    column_name = input('В какой колонке создать?: ')
    name = input('Задача: ')
    # Получим данные всех колонок на доске
    column_data = requests.get(BASE_URL.format('boards') + '/' +
                               board_id + '/lists', params=auth_params).json()
    # Переберём данные обо всех колонках, пока не найдём ту колонку, которая нам нужна
    for column in column_data:
        if column['name'] == column_name:
            # Создадим задачу с именем _name_ в найденной колонке
            requests.post(BASE_URL.format(
                'cards'), data={'name': name, 'idList': column['id'], **auth_params})
            cprint(f'Задача [{name}] успешно добавлена в [{column_name}]', 'green')
            return
    cprint('Задача не добавлена!', 'red')


def create_column(long_board_id, auth_params):
    clear_screen()
    column_name = input('Название новой колонки: ')

    while not column_name:
        clear_screen()
        cprint('Название не может быть пустым', 'red')
        column_name = input('Название новой колонки: ')

    params = {'name': column_name, 'idBoard': long_board_id, **auth_params}
    response = requests.post(BASE_URL.format('lists'), params=params)
    if response.status_code == 200:
        cprint(f'Колонка [{column_name}] успешно создана', 'green')
    else:
        cprint(f'Не удалось создать колонку [{column_name}]', 'red')


def move(board_id, auth_params):
    clear_screen()
    show_tasks(board_id, auth_params)
    name = input('Какую задачу переместить: ')
    # Получим данные всех колонок на доске
    column_data = requests.get(BASE_URL.format('boards') + '/' +
                               board_id + '/lists', params=auth_params).json()

    # Среди всех колонок нужно найти все задачи с нужным именем и закинуть в список
    tasks = []
    for column in column_data:
        column_tasks = requests.get(BASE_URL.format('lists') + '/' +
                                    column['id'] + '/cards', params=auth_params).json()
        for task in column_tasks:
            if task['name'] == name:
                tasks.append([task['id'], column['name']])

    if not tasks:
        cprint('Задача не найдена', 'red')
        return

    task_id = tasks[0][0]
    # Если задач в списке больше одной, вывести пронумерованные задачи
    if len(tasks) > 1:
        cprint(f'\nНайдено задач: {len(tasks)}', 'green')
        for i, task in enumerate(tasks):
            print(f'{i+1}. {name} в [{task[1]}]')
        print()

        # Дать пользователю выбрать номер нужной задачи
        n = None
        while n not in range(1, len(tasks) + 1):
            try:
                n = int(input('Введите номер нужной задачи: '))
                if n < 1:
                    raise LessThanOneValueError
                task_id = tasks[n - 1][0]
            except (ValueError, IndexError, LessThanOneValueError):
                cprint('Неправильное значение', 'red')

    column_name = input('В какую колонку?: ')
    # Теперь, когда у нас есть id задачи, которую мы хотим переместить
    # Переберём данные обо всех колонках, пока не найдём ту, в которую мы будем перемещать задачу
    for column in column_data:
        if column['name'] == column_name:
            # И выполним запрос к API для перемещения задачи в нужную колонку
            requests.put(BASE_URL.format('cards') + '/' +
                         task_id + '/idList', data={'value': column['id'], **auth_params})
            cprint(f'Задача [{name}] переносена в [{column_name}]', 'green')
            return
    cprint('Задача не пересена!', 'red')


def main():
    try:
        with open('user_data.json') as f:
            data = json.load(f)
            auth_params = data['auth_params']
            board_id = data['board_id']
    except:
        auth_params = get_auth_params()
        board_id = input('И ID доски: ')

    status_code = check_connection(auth_params, board_id)
    while status_code != 200:
        auth_params = get_auth_params('Не удаётся подключиться. Проверьте введённые данные.')
        board_id = input('И ID доски: ')
        status_code = check_connection(auth_params, board_id)
    save_user_data(auth_params, board_id)

    response = requests.get(f'https://trello.com/b/{board_id}/reports.json', params=auth_params)
    long_board_id = response.json()['id']

    command = ''
    while True:
        try:
            if command == 'tasks':
                show_tasks(board_id, auth_params)
                print('\nENTER - вернуться назад')
                command = input('> ').lower().strip()
            elif command == 'create task':
                create_task(board_id, auth_params)
                print('\nENTER - вернуться назад')
                command = input('> ').lower().strip()
            elif command == 'create column':
                create_column(long_board_id, auth_params)
                print('\nENTER - вернуться назад')
                command = input('> ').lower().strip()
            elif command == 'move':
                move(board_id, auth_params)
                print('\nENTER - вернуться назад')
                command = input('> ').lower().strip()
            elif command == 'exit':
                sys.exit(0)
            else:
                show_help()
                command = input('> ').lower().strip()
        except (KeyboardInterrupt, EOFError):
            sys.exit('\nBye!')


if __name__ == '__main__':
    main()
