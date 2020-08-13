import gen_world_ca
import os
from os.path import basename
from zipfile import ZipFile
import datetime


def is_world(s):
  return '.world' in s


def is_grid(s):
  return 'grid_' in s


def is_path(s):
  return 'path_' in s


def is_difficulty(s):
  return 'difficulties_' in s


def is_pgm(s):
  return '.pgm' in s


def zipFilesInDir(dirName, zipFileName, filter):
  # create ZipFile object
  with ZipFile(zipFileName, 'w') as zipObj:
    # iterate over files in directory
    for folderName, subfolders, filenames in os.walk(dirName):
      for filename in filenames:
        if filter(filename):
          # create complete filepath of file in directory
          filePath = os.path.join(folderName, filename)
          zipObj.write(filePath, basename(filePath))


def main():
  total_counter = 0

  # fill percent from 0.07 to 0.27, interval 0.05 (5 iterations)
  for i in range(5):
    fillPct = (i * 0.05) + 0.07
    # smooth iterations from 1 to 4, inclusive
    for smooths in range(1, 5):
      param_counter = 0
      while param_counter < 1:
        result = gen_world_ca.main(total_counter, hash(datetime.datetime.now()), smooths, fillPct)
        if result:
          print("world", total_counter, "fillPct", fillPct, "smooths", smooths)
          param_counter += 1
          total_counter += 1

  # get current directory
  curr_dir = os.getcwd()
  print(curr_dir)

  # zip files
  zipFilesInDir(curr_dir, 'Generated Worlds.zip', is_world)
  zipFilesInDir(curr_dir, 'Generated Grids.zip', is_grid)
  zipFilesInDir(curr_dir, 'Generated Paths.zip', is_path)
  zipFilesInDir(curr_dir, 'Generated Difficulties.zip', is_difficulty)
  zipFilesInDir(curr_dir, 'Generated Pgms.zip', is_pgm)


if __name__ == "__main__":
  main()
