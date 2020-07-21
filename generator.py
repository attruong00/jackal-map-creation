import gen_world_ca
import sys
import os
from zipfile import ZipFile

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
    smooths = 5
    fillPct = 0.35
    showHeatMap = 0

    # generate worlds
    for i in range(50):
      gen_world_ca.main(i, smooths, fillPct, showHeatMap)

    # zip files
    zipFilesInDir('~/jackal_ws/src/jackal_simulator/jackal_gazebo/worlds/', 'sampleWorlds.zip', lambda name : '.world' in name)
    zipFilesInDir('~/jackal_ws/src/jackal_simulator/jackal_gazebo/worlds/', 'sampleMaps.zip', lambda name : '.npy' in name)


if __name__ == "__main__":
    main()
