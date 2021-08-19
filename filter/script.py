#!/usr/bin/env python3

import os
import yaml
import sys
import csv


def cfg_read(config_path):
    """
    """

    with open(config_path, 'r') as cfgfile:
        config = yaml.load(cfgfile, Loader=yaml.FullLoader)

    return config


def sort_arr_dict(arr):
    """
    """

    cntr = True
    while cntr:
        cntr = False
        for i in range(len(arr) - 1):
            if arr[i]["vol"] < arr[i + 1]["vol"]:
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                cntr = True

    return arr


def catalogs_check_prepare(scrp, inp, out, in_near, ou_near, sep, files):
    """
    """

    # Are this paths in one directory with script or not?
    if in_near:
        input_path = scrp+inp
    else:
        input_path = inp

    if ou_near:
        output_path = scrp+out
    else:
        output_path = out

    # Are this paths have separator in the tail?
    if input_path[len(input_path)-1] != sep:
        input_path += sep

    if output_path[len(output_path)-1] != sep:
        output_path += sep

    # Are input catalog exist already?
    if not os.path.isdir(input_path):
        print("[ERR: Can't find input catalog (or it's empty)!]\n\
               Path: {}\nExiting with code 1.".format(input_path))
        sys.exit(1)
    elif len(os.listdir(input_path)) == 0:
        print("ERR: Input catalog is empty!\nPath: {}\n\
               Exiting with code 1.".format(input_path))
        sys.exit(1)

    # If output catalog doesn't exist: creating it.
    if not os.path.isdir(output_path):
        os.mkdir(output_path)

    # Also check all files in input cat
    for item in files:
        if not os.path.isfile(input_path+item["name"]):
            print("[ERR: File {} not found!]\nExiting with code 1.".
                  format(input_path+item["name"]))
            sys.exit(1)

    return input_path, output_path


def create_lists_for_update_queue(cfg, input_file, output_file):
    """
    I'm really sorry for this.
    Preparing CSV with old firmware.
    """

    buf = []
    tmp_list = []
    stat_total_entries = 0
    stat_filtered_entries = 0
    stat_unknown_ua = 0
    stat_is_there_ignored_uid = 0
    stat_with_req_firmware = 0
    stat_another_dt_type = 0
    stat_ignored_uid = None

    if cfg["exclusions_list"] is not None:
        stat_ignored_uid = dict.fromkeys(cfg["exclusions_list"])
    else:
        stat_ignored_uid = None

    if stat_ignored_uid is not None:
        for key in stat_ignored_uid.keys():
            stat_ignored_uid[key] = 0

    # Read file
    with open(input_file, 'r') as csf:
        csv_rdr = csv.reader(csf, delimiter=cfg["csv_delimiter"])
        for row in csv_rdr:
            buf.append(row)
            stat_total_entries += 1

    stat_total_entries -= 1  # Remove header from stat

    # Check for labels and save coordinates for this labels
    for item in cfg["mapping"]:
        if item["field_name"] not in buf[0]:
            print("Can't find {} tag in {}! Check this file please.\n\
                  Exiting with code 1.".format(item, tmp_filepath))
            sys.exit(1)
        else:
            item["index"] = buf[0].index(item["field_name"])

    # Filter
    # Core logic
    # If you want to add some conditions - do it here.
    for i in range(1, len(buf)):
        counter = 0
        full_match = 3

        for item in cfg["mapping"]:

            # Check distribution type
            if item["name"] == "DT":
                if buf[i][item["index"]] == infile["type"]:
                    counter += 1
                else:
                    stat_another_dt_type += 1

            # Check - if firmware seems already updated - then skip
            # otherwise - mark.
            # Also if we can't found vendor in UA - skip that line.
            if item["name"] == "FW":
                if buf[i][item["index"]].upper().find(
                 cfg["vendor"].upper()) == -1:
                    print(
                      "-> [WARN: Unknown UA (won't be added to loadout): {}]".
                      format(buf[i][item["index"]]))
                    stat_unknown_ua += 1
                else:
                    if buf[i][item["index"]].upper().find(
                     cfg["current_version_fw"].upper()) == -1:
                        counter += 1
                    else:
                        stat_with_req_firmware += 1

            # If UID not in exclusion list - mark them as "OK"
            if item["name"] == "UID":
                if cfg["exclusions_list"] is not None:
                    if buf[i][item["index"]] not in cfg["exclusions_list"]:
                        counter += 1
                    else:
                        stat_is_there_ignored_uid = True  # Dirty step
                        for key in stat_ignored_uid.keys():
                            if key == buf[i][item["index"]]:
                                stat_ignored_uid[key] += 1
                                break  # [!]
                else:
                    counter += 1

        # If we have full combo - adding this entry to temp
        if counter == full_match:
            tmp_list.append(buf[i])
            stat_filtered_entries += 1

    # Unload temp to file, also adding the header from original file
    if len(tmp_list) != 0:
        with open(output_file, 'w') as out_f:
            out_f.write(cfg["csv_delimiter"].join(buf[0])+"\n")
            for line in tmp_list:
                out_f.write(cfg["csv_delimiter"].join(line)+"\n")

    print("\n-> Stats:")
    print("-- Total rows: {}".
          format(str(stat_total_entries)))
    print("-- Matched rows: {}".
              format(str(stat_filtered_entries)))
    print("-- Discarded rows: {}".
          format(str(stat_total_entries-stat_filtered_entries)))
    print("--- With non-{} type: {}".
          format(infile["type"], str(stat_another_dt_type)))
    print("--- With {} firmware: {}".
          format(cfg["current_version_fw"], str(stat_with_req_firmware)))
    print("--- With unknown UserAgent: {}".format(str(stat_unknown_ua)))
    if stat_is_there_ignored_uid:
        print("--- Also following UID(s) has been ignored: ")
        for key in stat_ignored_uid.keys():
            if stat_ignored_uid[key] != 0:
                print("--- # {} ({} entries)".format(
                    key,
                    stat_ignored_uid[key]))
    else:
        print("--- Also there weren't any ignored uid's")

    # Return new version of mapping (with indexes)
    return cfg["mapping"]


def create_uniq_users_id(
      indexes, limits, input_file, output_file, dt_type):
    """
    """

    uid_pos = 0
    dl_pos = 0

    # Get coord for uid
    for i in indexes:
        if i["name"] == "UID":
            uid_pos = i["index"]
        if i["name"] == "DT":
            dl_pos = i["index"]

    uniq_uid = []

    with open(input_file, 'r') as csf:
        csv_rdr = csv.reader(csf, delimiter=cfg["csv_delimiter"])
        for row in csv_rdr:
            if row[dl_pos].upper() == dt_type.upper() and\
              row[uid_pos] not in uniq_uid:
                uniq_uid.append(row[uid_pos])

    with open(output_file, 'w') as uniq_out:
        for line in uniq_uid:
            uniq_out.write("{}\n".format(line))


def create_dl_list_for_update(
      limit_uid, limit_type, prefix, input_file, output_file, indexes):
    """
    I'm really sorry for this. (2)
    Preparing TXT file for update
    """

    buf = []
    uid_pos = 0
    dl_pos = 0
    dt_pos = 0

    stat_big_group = 0

    # Get coord for uid
    for i in indexes:
        if i["name"] == "UID":
            uid_pos = i["index"]
        if i["name"] == "DL":
            dl_pos = i["index"]

    # Unload to buf
    with open(input_file, 'r') as csf:
        csv_rdr = csv.reader(csf, delimiter=cfg["csv_delimiter"])
        for row in csv_rdr:
            buf.append(row)

    # Remove header
    t = buf.pop(0)

    # Get all uniq user ids
    uniq_uid = []

    for line in buf:
        if line[uid_pos] not in uniq_uid:
            uniq_uid.append(line[uid_pos])

    # Create index template
    index = []
    for uid in uniq_uid:
        index.append({"uid": uid, "vol": 0, "awr": 0})

    uniq_uid = None

    # Count how many devices per customer we have and limit it
    for line in buf:
        for entry in index:
            if entry["uid"] == line[uid_pos]:
                entry["vol"] += 1
                break  # [!]

    for entry in index:
        if entry["vol"] >= limit_uid:
            stat_big_group = 1
            break  # [!]

    # Creating a loadout accoring to limits

    sorted_index = sort_arr_dict(index)

    loadout_buf = []

    for entry in sorted_index:
        for line in buf:
            if line[uid_pos] == entry["uid"]:
                if entry["awr"] < entry["vol"] and entry["awr"] < limit_uid:
                    loadout_buf.append(line[dl_pos])
                    entry["awr"] += 1

    if len(loadout_buf) != 0:
        with open(output_file, "w") as out_file:
            out_file.write(prefix+"\n")
            counter = 0
            for line in loadout_buf:
                if counter < limit_type:
                    out_file.write(line+"\n")
                    counter += 1
                else:
                    break  # [!]

    if len(loadout_buf) >= limit_type:
        print("-- Prepared to update: {} [WARN: Out of limit! ({})]".
              format(str(len(loadout_buf)), str(limit_type)))
    else:
        print("-- Prepared to update: {}".format(str(len(loadout_buf))))

    if stat_big_group:
        print("-- Big group(s) in this loadout:")
        for entry in index:
            if entry["vol"] >= limit_uid:
                print("--- # {}: {} ({} prepared to update)".format(
                    entry["uid"], entry["vol"], entry["awr"]))

    return len(loadout_buf)


if __name__ == "__main__":
    """
    """
    config_name = "config.yml"
    script_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    file_counter = 0

    if script_path.find("/") != -1:
        separator = script_path[script_path.find("/")]
    else:
        separator = script_path[script_path.find("\\")]

    script_path += separator

    config_path = "{}{}".format(script_path, config_name)

    print("=" * 10 +
          "\n\n>>> The Vasyan's Factory of Crutches and Bicycles <<<\n\n" +
          " " * 9 + " >>> FW lists cutter v.0.1.a <<<\n\n" + "=" * 10 + "\n")

    print("> Reading configfile")
    cfg = cfg_read(config_path)

    print("> Checking in/out catalogs and input files")
    input_path, output_path = catalogs_check_prepare(
        script_path,
        cfg["input_cat"],
        cfg["output_cat"],
        cfg["input_near_script"],
        cfg["output_near_script"],
        separator,
        cfg["files"])

    print("\n"+"-"*10+"\n")

    for entry in cfg["limits"]:
        entry["total"] = 0

    for infile in cfg["files"]:
        print("-> Processing: {}".format(input_path+infile["name"]))
        print("-- | Params | LOCATION {} | TYPE {} |\n"
              .format(str(infile["location"]), infile["type"]))
        output_file_name = "{}_LOCATION{}_{}".format(
            cfg["vendor"],
            str(infile["location"]),
            infile["type"])

        limit_value = 0

        is_list_needed = False

        for limit in cfg["limits"]:
            if infile["type"].upper() == limit["type"].upper():
                limit_value = limit["value"]
                if limit["is_uniq_id_list_needed"]:
                    is_list_needed = limit["is_uniq_id_list_needed"]
                    limit_name = limit["type"]
                break  # [!]

        csv_outfile = "{}{}_1_{}.csv".format(
            output_path,
            str(file_counter),
            output_file_name)

        cfg["mapping"] = create_lists_for_update_queue(
            cfg,
            input_path+infile["name"],
            csv_outfile)

        if os.path.isfile(csv_outfile):
            txt_outfile = "{}{}_2_{}_update.txt".format(
                output_path,
                str(file_counter),
                output_file_name)

            if is_list_needed:
                unq_outfile = "{}{}_3_{}_uniq_list.txt".format(
                    output_path,
                    str(file_counter),
                    output_file_name,
                    limit_name)

                create_uniq_users_id(
                    cfg["mapping"],
                    cfg["limits"],
                    input_path+infile["name"],
                    unq_outfile,
                    limit_name)

            lines_tmp = create_dl_list_for_update(
                cfg["limit_per_uid"],
                limit_value,
                cfg["prefix"],
                csv_outfile,
                txt_outfile,
                cfg["mapping"])

            for entry in cfg["limits"]:
                if entry["type"] == infile["type"]:
                    entry["total"] += lines_tmp
        else:
            print("\n")
            print("-- [WARN: There weren't devices for LOCATION {} with {} type.]".
                  format(str(infile["location"]), infile["type"]))

        print("\n"+"-"*10+"\n")
        file_counter += 1

    print("> Total number of devices which ready to update: ")
    for entry in cfg["limits"]:
        if entry["total"] < entry["value"]:
            print("- {}: {} of {}".
                  format(entry["type"], entry["total"], entry["value"]))
        else:
            print("- {}: {} of {} [WARN: Out of limit!]".
                  format(entry["type"], entry["total"], entry["value"]))

    print("\n> Done. Output files in: {}\n".format(output_path))
    print("="*10+"\n\n >>> Konetz <<<\n\n"+"="*10+"\n")
