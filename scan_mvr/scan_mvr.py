#!/usr/bin/python2
#-*- coding: utf-8 -*-

import os, time

def catalog_generate(path):
	'''
        Собираем перечень файлов в каталоге
	'''
	barcode_list = []
	for i in os.walk(path):
			for scan in os.listdir(i[0]):
				barcode_list.append(i[0]+scan)
	return barcode_list


def move_file(filepath, catpath):
	'''
	Переносит файл в соотв. каталог
	'''

	os.system('mv '+filepath+' '+catpath)
	return (filepath+';moved to;'+catpath)

def add_to_log(text):
	'''
	Временно костылим лог
	'''

	os.system("echo \""+text+"\" >> scc_log_os2.txt")


if __name__ == "__main__":

        path_from = './queue/'
        path_to = './scan_source/'
        delay_between_scans = 1
        delay_between_portions = 7200
        max_doc_per_launch = 25

        file_arr = catalog_generate(path_from)
        
        while len(file_arr) != 0:

            file_arr = catalog_generate(path_from)

            if len(file_arr) < max_doc_per_launch:
                print('Change MDPL from '+str(max_doc_per_launch)+' to '+str(len(file_arr)))
                max_doc_per_launch = len(file_arr)

            for i in range(0, max_doc_per_launch):
                t = move_file(file_arr[i], path_to)
                print(t)
                time.sleep(delay_between_scans)

            file_arr = catalog_generate(path_from)
            print('Est.: '+str(len(file_arr)))

            if len(file_arr) == 0:
                break
            else:
                time.sleep(delay_between_portions)
        
        print('Folder is empty. Exiting')

