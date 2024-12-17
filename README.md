# Flightradar24 2 KML

A program for downloading [Flightradar24](https://globe.adsbexchange.com/) tracks, and export to KML/GPX formats.

## Table of content

- [Flightradar24 2 KML](#flightradar24-2-kml)
  - [Table of content](#table-of-content)
  - [Introduction](#introduction)
  - [Getting the program](#getting-the-program)
    - [Presrequisites](#presrequisites)
    - [Installation](#installation)
  - [Using the program](#using-the-program)
    - [Parameters](#parameters)

## Introduction

This program will fetch the tracks within 7 days of a given aircraft given its registration.


## Getting the program

### Presrequisites

This program uses [python3](https://www.python.org/) and [requests module](https://pypi.org/project/requests/) of python3.

Download and install python3 from [here](https://www.python.org/downloads/), and install `requests` using:

```
pip3 install requests
```

### Installation

You can either use `git` to install the program, or just download the whole program in `.zip` format from [here](https://github.com/chaoshaowei/flightradar-kml/archive/refs/heads/master.zip)

Install:
```
git clone https://github.com/chaoshaowei/flightradar-kml.git
```

Update:
```
git pull https://github.com/chaoshaowei/flightradar-kml.git
```

## Using the program

Now the newest file is `mainargparse.py`, and `main.py` will soon be deleted.
Maybe there will be graphical interface to get tracks in the future.

For now, the program can only be used using command prompt.

The output file will be renamed based on the plane's registration, and the requested date. The default time format will be based on FR24 Destination's timezone, and could be customized.

### Basic usage

There are a few runmodes of the program:

#### **-r0**, List all flights performed by an aircraft reg
```
python3 mainargparse.py -r0 REG
```
This will list all the FR24 HEX IDs into a file in "HEXs" folder, but not actually downloading the track data.

#### **-r1**, Download all flights performed by an aircraft reg
```
python3 mainargparse.py -r1 REG
```
Similar to `-r0`, but this time also download and process the actual track data.

#### **-r3**, Download all flights specified by FR24 HEX IDs
```
python3 mainargparse.py -r3 [HEX_ID1 ...]
```
If you already know the HEX IDs you want to download, just list then here, and the program will download only those tracks.

`-r2` mode is similar, but it could only take 1 HEX ID, and will soon be removed

#### **-r4**, Walkthrough all HEX IDs between two FR24 HEX IDs
```
python3 mainargparse.py -r4 HEX_ID1 HEX_ID2
```
This mode is only useful if you know the approximate departure time of a flight, but didn't recorded its actual HEX ID.
You need to first find two HEX IDs, with similar departure time, and hoping that somehow your target flight's HEX ID was between the two bounding HEX IDs.

FR24's HEX IDs are somehow sorted, based on the time of first acquired ADS-B data of the flight, so it is similar to say that the HEX IDs are sorted based on their departure time.

#### **-r5**, List all flights performed by an aircrafts listed in `fleet_list.txt`
```
python3 mainargparse.py -r5
```
Similar to `-r0`, but this will list all HEX IDs by ALL aircrafts in `fleet_list.txt`

For now, the program will ignore any line starting with `#`, but please do not contain non-reg line in `fleet_list.txt`, including empty lines

### Optional arguments

There are some optional arguments to add after the basic runmode argument.
Most of the time, different optional arguments could be used together.

#### **-tzm**, To change the time format used when outputing GPX/KML files
```
python3 mainargparse.py (BASIC RUNMODE) -tzm {0, 1, 2}
```
- 0, UTC   : 2023-09-08T1230Z
- 1, CUSTOM: 2023-09-08T2030+0800 (specified in "-tzo" option)
- 2, AUTO  : 2023-09-08T2030+0800 (use FR24 Destination's timezone, default)

#### **-tzo**, Used with `-tzm 1`, to specify a timezone used when outputing GPX/KML files
```
python3 mainargparse.py (BASIC RUNMODE) -tzm 1 -tzo 6.5
```
The result GPX/KML filename of this example, will be using the time in a custom timezone, with UTC OFFSET of +6hr30min.

e.g. 2023-09-08T1900+0630

#### **-ck**, use custom cookie and token
```
python3 mainargparse.py (BASIC RUNMODE) -ck
```
Please create two new files, `cookie.txt` and `token.txt`.

Just copy your cookie from the browser, and copy to `cookie.txt`.
For `token.txt`, find the value of `_frPl` in the cookie, and copy into the file.

This is useful if you have premium membership, and using `-r0`or`-r5`

#### **-c**, Create additional copy into user specified folder
```
python3 mainargparse.py (BASIC RUNMODE) -c PATH
```
Just a good feature, if you like to organize everything.

For me, I always do `-c .\Custom\Ian`, so that I could have a place only containing my flights, even if I sometimes download other flights as well.

## Using the program (Old `main.py`)

Simply edit the reg in `main.py`, then run the python script.

The output file will be renamed based on the plane's registration, and the requested date. The time will be based on the event time of the flight, localized into timezone described in [`OUTPUT_TZ`].

Currently, the option of using the code requires you to modify the `main.py` file, and change the reg and/or the date.

Maybe there will be graphical interface to get tracks in the future.

### Parameters

Basic parameters:

* `REG_ID` = [`String`]: The targeting aircraft registration
* `FLIGHT_ID` = [`String`]: The targeting flightradar24 flight ID, which is a 24-bit hex string, if `RUN_MODE` is set to `SEARCH_FLIGHT_BY_FLIGHT_ID`

Advanced parameters:

* `OUTPUT_TZ_NUM` = [`Number`]: The hours difference from GMT, which will be in the output filename
* `RUN_MODE` = [`ENUM/Number`]: The running mode of the program
  * `LIST_FLIGHT_BY_REG`: Just list out the flights of an aircraft in the past 7 days
  * `SEARCH_FLIGHT_BY_REG`: Download all flights of an aircraft in the past 7 days
  * `SEARCH_FLIGHT_BY_FLIGHT_ID`: Download a specific flight
* `OUTPUT_KML`: [`True`/`False`]: Export KML or not
* `OUTPUT_GPX`: [`True`/`False`]: Export GPX or not
