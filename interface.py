from base import Monitor, Logger, DataBase

import sys
import asyncio


class TimeMonitor:
    def __init__(self):
        self.db = DataBase()
        self.logger = Logger(self.db)
        self.monitor = Monitor(self.logger)
        self.loop = asyncio.get_event_loop()
        self.q = asyncio.Queue()
        self.to_stop = False
        self.to_pause = False
        self.loop.add_reader(sys.stdin, self.got_input)

    def run(self):
        try:
            tasks = [self.sniff(), self.operation()]
            self.loop.run_until_complete(asyncio.wait(tasks))
        except KeyboardInterrupt:
            print('timeMonitor is shutting down')
            self.db.c.close()
            self.db.conn.close()
            sys.exit()

    def got_input(self):
        data = sys.stdin.readline()
        asyncio.ensure_future(self.q.put(data))

    async def sniff(self):
        print('timeMonitor is running!!!')
        while not self.to_stop:
            if self.to_pause:
                await asyncio.sleep(30)
                continue
            self.monitor.run()
            await asyncio.sleep(30)

    async def operation(self):
        while True:
            _input = await self.q.get()
            _input = _input.rstrip()
            if _input == 'p':
                print('timeMonitor is pausing')
                self.to_pause = True
            elif _input == 'r':
                print('timeMonitor is resuming!')
                self.to_pause = False
            elif _input == 'q':
                print('timeMonitor is shutting down')
                self.to_stop = True
                self.db.c.close()
                self.db.conn.close()
                sys.exit()
            elif _input == 'e':
                self.edit_cats()
            else:
                self.query(_input)

    def query(self, date):
        if date.isdigit:
            if len(date) == 8:
                self.db.query_day(date)
            elif len(date) == 6:
                self.db.query_month(date)
            elif len(date) == 4:
                self.db.query_year(date)
            else:
                print('Please use format like 20190302 or 201903 or 2019')
        else:
            print('query input should be digit')

    def edit_cats(self):
        tag_dic = {'1': "Productive", '2': 'Neutral', '3': 'Distracting', '4': 'Uncategorized'}
        _input = input('Press 1 to edit uncategorized apps/webs\n'
                       'Press 2 to edit categorized apps/webs\n'
                       'or press anything you want to quit\n')
        if _input == '1':
            _name, _tag_num = self.db.list_all_uncats()
        elif _input == '2':
            _name, _tag_num = self.db.fuzzy_search()
        else:
            print('Quit edit')
            return
        if _name and _tag_num:
            self.logger.update_cats(_name, tag_dic[_tag_num])
            self.db.update_tag(_name, tag_dic[_tag_num])
            print('{} has been categorized as: {}'.format(_name, self.logger.cats[_name]))
        else:
            print('Quit edit')

