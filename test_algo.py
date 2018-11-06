#!/usr/bin/python3

import csv
import copy
import sys
import re, itertools

WHITELIST = ['account_accountant','crm','website','stock','project','purchase','sale_management']

with open('module_time.csv', 'r') as mt:
    reader = csv.reader(mt, delimiter=',', quotechar='"')
    mod_time = dict(map(lambda x: (x[0], float(x[1])), reader))
BLACKLIST = [key for key,value in mod_time.items() if value<10.0]

mod_dep = {
    'account': ['mail'],
    'account_accountant': ['mail', 'account'],
    'board': [],
    'calendar': ['mail'],
    'contacts': ['mail'],
    'crm': ['calendar', 'mail', 'contacts'],
    'documents': ['mail'],
    'fleet': ['mail'],
    'helpdesk': ['mail'],
    'hr': ['mail'],
    'hr_appraisal': ['calendar', 'mail', 'survey', 'hr'],
    'hr_attendance': ['mail', 'hr'],
    'hr_expense': ['mail', 'account', 'hr'],
    'hr_holidays': ['calendar', 'mail', 'hr'],
    'hr_recruitment': ['calendar', 'mail', 'hr'],
    'im_livechat': ['mail'],
    'iot': ['mail'],
    'lunch': ['mail'],
    'mail': [],
    'maintenance': ['mail'],
    'marketing_automation': ['mass_mailing', 'mail', 'contacts'],
    'mass_mailing': ['mail', 'contacts'],
    'mrp': ['mail', 'stock'],
    'mrp_plm': ['mail', 'mrp', 'stock'],
    'note': ['mail'],
    'point_of_sale': ['mail', 'account', 'stock'],
    'project': ['mail'],
    'project_forecast': ['mail', 'project', 'hr'],
    'purchase': ['mail', 'account'],
    'quality_control': ['mail', 'stock'],
    'repair': ['mail', 'account', 'stock', 'sale_management'],
    'sale_management': ['mail', 'account'],
    'sale_subscription': ['mail', 'account', 'sale_management'],
    'sign': ['mail'],
    'stock': ['mail'],
    'stock_barcode': ['mail', 'stock'],
    'survey': ['mail'],
    'timesheet_grid': ['mail', 'project', 'hr'],
    'voip': ['mail'],
    'web_studio': ['mail'],
    'website': ['mail'],
    'website_blog': ['website', 'mail'],
    'website_calendar': ['website', 'mail', 'calendar', 'hr'],
    'website_event': ['website', 'mail'],
    'website_forum': ['website', 'mail'],
    'website_hr_recruitment': ['website',
                            'mail',
                            'hr_recruitment',
                            'calendar',
                            'hr'],
    'website_livechat': ['website', 'mail', 'im_livechat'],
    'website_sale': ['website', 'mail', 'account'],
    'website_slides': ['website', 'mail'],
}

def get_modules():
    with open('modules_installed.csv', 'r') as mi:
        reader = csv.reader(mi, delimiter=',', quotechar='"')
        return list(map(lambda x: list(set(x[2].strip(':').split(':'))), reader))

class db(object):
    def __init__(self):
        self.time = 0.0
        self.dbs = {}
        self.db_re = {}
        self.times = []

    def get_time(self, modules):
        time = mod_time['base']
        for m in modules:
            time += mod_time.get(m, 0.0)
        return time

    def get_dependencies(self, mods):
        mods2 = mods[:]
        done = []
        while mods2:
            m = mods2.pop(0)
            done.append(m)
            for mod in mod_dep.get(m, []):
                if mod not in mods:
                    mods.append(mod)
                    mods2.append(mod)
        return mods

    def mod_sort(self, mods):
        mods.sort(key = lambda x: mod_time.get(x, 0.0))
        return mods

    def mod_hash(self, mods):
        self.mod_sort(mods)
        mods_str = ','.join(mods)+','
        return mods_str, re.compile(',.*'.join(mods)+',')

    def process_dummy(self, mods):
        mods = self.get_dependencies(mods)
        mods_str, mods_re = self.mod_hash(mods)
        if mods_str in self.dbs:
            self.times.append(0)
        else:
            self.time += self.get_time(mods)
            self.times.append(self.get_time(mods))
        self.dbs[mods_str] = mods_re

    def process_whitelist_prebuild(self):
        for nbr in range(2,len(WHITELIST)+1):
            for mods in itertools.combinations(WHITELIST, nbr):
                mods = list(mods)
                mods_str, mods_re = self.mod_hash(mods)
                self.dbs[mods_str] = mods_re
                self.time += self.get_time(mods)

    def process_whitelist(self, mods):
        mods = self.get_dependencies(mods)
        mods_whitelist = [x for x in mods if x in WHITELIST]
        mods_str, mods_re = self.mod_hash(mods)
        if mods_str in self.dbs:
            self.times.append(0)
        else:
            for nbr in range(len(mods_whitelist), 0, -1):
                best = 0
                for try_mods in itertools.combinations(mods_whitelist, nbr):
                    try_mods = self.get_dependencies(list(try_mods))
                    try_str, _ = self.mod_hash(try_mods)
                    if try_str in self.dbs:
                        best = max(self.get_time(try_mods), best)
                if best:
                    self.time += self.get_time(mods) - best
                    self.times.append(self.get_time(mods) - best)
                    break
            else:
                self.time += self.get_time(mods)
                self.times.append(self.get_time(mods))

        self.dbs[mods_str] = mods_re


    def process_subset(self, mods):
        mods = self.get_dependencies(mods)
        mods_str, mods_re = self.mod_hash(mods)
        time = self.find_subset(mods)
        self.time += self.get_time(mods) - time
        self.times.append(self.get_time(mods) - time)
        self.dbs[mods_str] = mods_re

    def process_subset_blacklist(self, mods):
        self.process_subset(mods)
        mods_whitelist = [x for x in mods if x not in BLACKLIST]
        self.get_dependencies(mods_whitelist)
        mods_str, mods_re = self.mod_hash(mods_whitelist)
        self.dbs[mods_str] = mods_re

    def find_subset(self, mods):
        time = 0
        mods_str, _ = self.mod_hash(mods)
        for db, db_re in self.dbs.items():
            if db_re.findall(mods_str):
                time = max(time, self.get_time(db.strip(',').split(',')))
        return time

    def stats(self):
        print ('# Databases  {}'.format(len(self.dbs)))
        print ('AVG Time     {}s'.format(round(self.time / len(self.times), 2)))
        self.times.sort()
        p50 = self.times[len(self.times)//2]
        p95 = self.times[int(len(self.times)*.95)]
        p99 = self.times[int(len(self.times)*.99)]
        print ('p50 p95 p99  {}s {}s {}s'.format(p50, p95, p99))


mods = get_modules()
if len(sys.argv)>1:
    mods = mods[:int(sys.argv[1])]

print ("ALL OR NOTHING - DUMMY COMPUTATION")
dummy = db()
for m in mods:
    dummy.process_dummy(m)
dummy.stats()

print ()
print ('SUBSET BASED ON WHITELIST')
subset = db()
for m in mods:
    subset.process_whitelist(m)
subset.stats()

print ()
print ('SUBSET BASED ON WHITELIST, WITH PREBUILD')
subset = db()
subset.process_whitelist_prebuild()
for m in mods:
    subset.process_whitelist(m)
subset.stats()

print ()
print ('OPTIMUM SUBSET')
subset = db()
for m in mods:
    subset.process_subset(m)
subset.stats()

print ()
print ('OPTIMUM SUBSET WITH EXTRA BUILD (BLACKLIST)')
subset = db()
for m in mods:
    subset.process_subset_blacklist(m)
subset.stats()


