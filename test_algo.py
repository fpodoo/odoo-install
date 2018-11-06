#!/usr/bin/python3

import csv
import copy
import re, itertools

WHITELIST = ['account','crm','website','stock','project']

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
        return list(map(lambda x: x[2].strip(':').split(':'), reader))

class db(object):
    def __init__(self):
        self.nbr_scratch = 0
        self.nbr_cache = 0
        self.nbr_30 = 0
        self.time = 0.0
        self.dbs = {}
        self.db_re = {}

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
                if mod not in (done+mods2):
                    mods.append(mod)
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
            self.nbr_cache += 1
        else:
            self.nbr_scratch += 1
            self.time += self.get_time(mods)
            if self.get_time(mods)>30: self.nbr_30+=1
        self.dbs[mods_str] = mods_re

    def process_whitelist_prebuild(self):
        for nbr in range(2,6):
            for mods in itertools.combinations(WHITELIST, nbr):
                mods = list(mods)
                mods_str, mods_re = self.mod_hash(mods)
                self.dbs[mods_str] = mods_re
                self.time += self.get_time(mods)
                if self.get_time(mods)>30: self.nbr_30+=1

    def process_whitelist(self, mods):
        mods = self.get_dependencies(mods)
        mods_whitelist = [x for x in mods if x in WHITELIST]
        mods_str, mods_re = self.mod_hash(mods)
        if mods_str in self.dbs:
            self.nbr_cache += 1
        else:
            time = self.find_subset(mods_whitelist)
            if time:
                self.nbr_cache += 1
                self.time += self.get_time(mods) - time
                if (self.get_time(mods)-time)>30: self.nbr_30+=1
            else:
                self.nbr_scratch += 1
                self.time += self.get_time(mods)
                if self.get_time(mods)>30: self.nbr_30+=1

        self.dbs[mods_str] = mods_re

    def process_subset(self, mods):
        mods = self.get_dependencies(mods)
        mods_str, mods_re = self.mod_hash(mods)
        time = self.find_subset(mods)
        if time:
            self.nbr_cache += 1
            self.time += self.get_time(mods) - time
            if (self.get_time(mods)-time)>30: self.nbr_30+=1
        else:
            self.nbr_scratch += 1
            self.time += self.get_time(mods)
            if self.get_time(mods)>30: self.nbr_30+=1
        self.dbs[mods_str] = mods_re

    def process_subset_blacklist(self, mods):
        self.process_subset(mods)
        mods_whitelist = [x for x in mods if x not in BLACKLIST]
        mods_str, mods_re = self.mod_hash(mods_whitelist)
        self.dbs[mods_str] = mods_re

    def find_subset(self, mods):
        time = 0
        mods_str = self.mod_hash(mods)[0]
        for db, db_re in self.dbs.items():
            if db_re.match(mods_str):
                time = max(time, self.get_time(db.strip(',').split(',')))
        return time

    def stats(self):
        # print ('Partial     {}: {}%'.format(self.nbr_scratch, round(self.nbr_scratch * 100 / (self.nbr_cache + self.nbr_scratch))))
        # print ('Cache       {}: {}%'.format(self.nbr_cache, round(self.nbr_cache * 100 / (self.nbr_cache + self.nbr_scratch))))
        print ('# Databases  {}'.format(len(self.dbs)))
        print ('DB Above 30s {} = {}%'.format(self.nbr_30, self.nbr_30 * 100 // (self.nbr_scratch+self.nbr_cache)))
        print ('AVG Time     {}s'.format(round(self.time / (self.nbr_scratch+self.nbr_cache), 2)))

mods = get_modules()

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


