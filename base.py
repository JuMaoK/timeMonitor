import time
from urllib.parse import urlparse
import json
import sqlite3
import datetime
import calendar

from AppKit import NSWorkspace
import appscript


class Window:
    '''记录初始时间，app name/web domain，tag=4大类'''
    def __init__(self, name=None, tag=None):
        self.name = name
        self.tag = tag


class Monitor:
    '''检测当前活跃窗口，一旦窗口变化，记录持续时间'''
    def __init__(self, logger):
        self.logger = logger
        self.last = None
        self.workspace = NSWorkspace.sharedWorkspace()

    def run(self):
        if self.last:
            self.logger.log(self.last)
        name = self.workspace.activeApplication()['NSApplicationName']
        url, domain = None, None
        if name.startswith('Safari'):
            url = appscript.app("Safari").windows.first.current_tab.URL()
        elif name == 'Google Chrome':
            url = appscript.app("Google Chrome").windows.active_tab.URL()[0]
        if url:
            name = urlparse(url).netloc
        tag = self.auto_sorting(name)
        self.last = Window(name=name, tag=tag)

    def auto_sorting(self, name):
        return self.logger.cats.get(name, None)


class Logger:
    '''记录每天活动时间，每天12点和20点更新数据库'''
    def __init__(self, db):
        try:
            with open('cats.json') as f:
                self.cats = json.load(f)  # TODO: 忽略名单
        except FileNotFoundError:
            with open('cats.json', 'w') as f:
                json.dump({}, f)
                self.cats = {}
        self.db = db
        self.today = datetime.date.today().strftime('%Y%m%d')

    def log(self, window):
        '''记录每个app/web的总时间'''
        if window.name not in self.cats:
            window.tag = 'Uncategorized'
            self.update_cats(window.name, window.tag)
        else:
            window.tag = self.cats[window.name]
        self.db.insert_or_update(window.name, self.today, window.tag, 0.5)

    def update_cats(self, name, tag):   # TODO：批量处理
        self.cats[name] = tag
        with open('cats.json', 'w') as f:
            json.dump(self.cats, f)


class DataBase:
    def __init__(self):
        self.conn = sqlite3.connect('timeM.db')
        self.c = self.conn.cursor()
        self.c.execute("CREATE TABLE IF NOT EXISTS data "
                       "(name TEXT, dt DATE, tag TEXT, time REAL, PRIMARY KEY(name, dt))")

    def close(self):
        self.c.close()
        self.conn.close()

    def insert_or_update(self, name, dt, tag, time_last):
        sql = "INSERT OR REPLACE INTO data VALUES(?, ?, ?, " \
                  "COALESCE((SELECT time FROM data WHERE name=? AND dt=?)+?, ?));"
        self.c.execute(sql, (name, dt, tag, name, dt, time_last, time_last))
        self.conn.commit()

    def update_tag(self, name, tag):
        sql = "UPDATE data SET tag=? WHERE name=?"
        self.c.execute(sql, (tag, name))
        self.conn.commit()

    def list_all_uncats(self):
        sql = "SELECT name FROM data WHERE tag='Uncategorized' GROUP BY name;"
        self.c.execute(sql)
        uncats = [name for row in self.c.fetchall() for name in row]
        for i, n in enumerate(uncats):
            print(i, ': ', n)
        idx = input('Please select a uncategorized item\n'
                    'or press anything except number to quit\n')
        if not idx.isdigit():
            return None, None
        try:
            _name = uncats[int(idx)]
            _tag_num = input('You want {} categorized as\n1: Productive, '
                             '2: Neutral, 3: Distracting, 4:Uncategorized\n'.format(_name))
            return _name, _tag_num
        except KeyError:
            print('Wrong number: ')
            return None, None

    def fuzzy_search(self):
        like = input('Please enter a keyword for search\n')
        like = '%' + like + '%'
        sql = "SELECT name, tag FROM data WHERE name LIKE ? GROUP BY name ;"
        self.c.execute(sql, (like, ))
        data = self.c.fetchall()
        if data:
            print('Results found: ')
            print(20 * '*')
            for i, res in enumerate(data):
                print(i, res[0], res[1])
            print(20 * '*')
            idx = input('Please select a item to edit\n'
                        'or press anything except number to quit\n')
            if not idx.isdigit():
                return None, None
            try:
                idx = int(idx)
                _name, _tag = data[idx]
                _tag_num = input('You want {} categorized as\n1: Productive, '
                                 '2: Neutral, 3: Distracting, 4:Uncategorized\n'.format(_name))
                return _name, _tag_num
            except IndexError:
                print('Wrong number')
                return None, None
        else:
            print('Nothing found')
            return None, None

    def query_day(self, dt):
        sql = "SELECT name, tag, time FROM data WHERE dt=? GROUP BY name ORDER BY time DESC"
        self.c.execute(sql, (dt,))
        print('{:<30} {:<15} {:>8}'.format('Name', 'Tag', 'Time'))
        print(60 * '*')
        for row in self.c.fetchall():
            name, tag, time_last = row
            print('{:<30} {:<15} {:>8}'.format(name, tag, time_last))
        print(60 * '*')

    def query_month(self, year_month):
        sql = "SELECT dt, tag, SUM(time) FROM data WHERE dt=? GROUP BY tag"
        _date = datetime.datetime.strptime(year_month, '%Y%m')
        _year = _date.year
        _month = _date.month
        month_end = calendar.monthrange(_year, _month)[1]

        print('{:12} {:15} {:>8}'.format('Date', 'Tag', 'Time'))
        for i in range(1, month_end+1):
            dt = year_month + format(i, '02')
            self.c.execute(sql, (dt,))
            last = None
            for row in self.c.fetchall():
                dt, tag, t = row
                if dt != last:
                    print(40 * '*')
                    print('{:<12} {:15} {:>8}'.format(dt, tag, t))
                    last = dt
                else:
                    print('{:12} {:15} {:>8}'.format('', tag, t))

    def query_year(self, year):
        sql = "SELECT tag, SUM(time) FROM data WHERE dt>=? and dt<=? GROUP BY tag"
        for i in range(1, 13):
            print('{:15}'.format(calendar.month_name[i]))
            year_month = year + format(i, '02')
            month_range = calendar.monthrange(int(year), i)[1]
            start = year_month + '01'
            end = year_month + format(month_range, '02')
            self.c.execute(sql, (start, end))
            for row in self.c.fetchall():
                tag, time = row
                print('{:15}: {:>8}'.format(tag, time), sep='\t\t')
            print(25 * '*')


