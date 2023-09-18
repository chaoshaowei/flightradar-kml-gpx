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
