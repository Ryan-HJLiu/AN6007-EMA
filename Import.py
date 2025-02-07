# -*- coding: utf-8 -*-
"""
Created on Fri Jan 24 11:31:19 2025

@author: Qihao Qi
"""
import csv


def read_record(f: str):
    """
    Read all records within a txt file on one timestamp into a list of records
    """
    with open (f, 'r') as file:
        next(file)
        lines = [line.strip() for line in file.readlines()]
    return lines

def daily_memory(final_l: list, line: list):
    """
    Transform this day's records into a listed list, append time by time
    """
    for i in line:
        sep = i.split(';')
        final_l.append(sep)
#    return final_list

def daily_prepare_store_record(l: list):
    """
    Add in titles for data and be ready to transfer into a csv file
    """
    rdy_to_store = [['meter_id', 'timestamp', 'reading']]
    for i in l:
        rdy_to_store.append(i)
    return rdy_to_store

def export_csv(l: list):
    """
    Export this day's records into a csv file on drive
    """
    filename = f"{l[1][2]}.csv"
    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(l)




