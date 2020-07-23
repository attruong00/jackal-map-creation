import random
import sys
import datetime
import Queue
import math
import matplotlib.pyplot as plt
import Tkinter as tk
from world_writer import WorldWriter
import numpy as np

def_kernel_size = 4

class ObstacleMap():
  def __init__(self, rows, cols, randFillPct, seed=None, smoothIter=5):
    self.map = [[0 for i in range(cols)] for j in range(rows)]
    self.rows = rows
    self.cols = cols
    self.randFillPct = randFillPct
    self.seed = seed
    self.smoothIter = smoothIter

  def __call__(self):
    self._randomFill()
    for n in range(self.smoothIter):
      self._smooth()

  def _randomFill(self):
    if self.seed:
      random.seed(self.seed)

    for r in range(self.rows):
      for c in range(self.cols):
        if r == 0 or r == self.rows - 1:
          self.map[r][c] = 1
        else:
          self.map[r][c] = 1 if random.random() < self.randFillPct else 0

  def _smooth(self):
    newmap = [[self.map[r][c] for c in range(self.cols)] for r in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        # if more than 4 filled neighbors, fill this tile
        if self._tileNeighbors(r, c) > 4:
          newmap[r][c] = 1

        # if less than 2 filled neighbors, empty this one
        elif self._tileNeighbors(r, c) < 2:
          newmap[r][c] = 0

    self.map = newmap

  def _tileNeighbors(self, r, c):
    count = 0
    for i in range(r - 1, r + 2):
      for j in range(c - 1, c + 2):
        if self._isInMap(i, j):
          if i != r or j != c:
            count += self.map[i][j]

        # if on the top or bottom, add to wall neighbors
        elif i < 0 or i >= self.rows:
          count += 1
    
    return count

  def _isInMap(self, r, c):
    return r >= 0 and r < self.rows and c >= 0 and c < self.cols

  # update the obstacle map given the jackal-space
  # coordinates that were cleared to ensure connectivity
  def updateObstacleMap(self, cleared_coords, kernel_size):
    for coord in cleared_coords:
      for r in range(coord[0], coord[0] + kernel_size):
        for c in range(coord[1], coord[1] + kernel_size):
          self.map[r][c] = 0

    return self.map

  def getMap(self):
    return self.map

class JackalMap:
  def __init__(self, ob_map, kernel_size):
    self.ob_map = ob_map
    self.ob_rows = len(ob_map)
    self.ob_cols = len(ob_map[0])

    self.kernel_size = kernel_size
    self.map = self._jackalMapFromObstacleMap(self.kernel_size)
    self.rows = len(self.map)
    self.cols = len(self.map[0])

  # use flood-fill algorithm to find the open region including (r, c)
  def _getRegion(self, r, c):
    queue = Queue.Queue(maxsize=0)
    region = [[0 for i in range(self.cols)] for j in range(self.rows)]
    size = 0

    if self.map[r][c] == 0:
      queue.put((r, c))
      region[r][c] = 1
      size += 1

    while not queue.empty():
      coord_r, coord_c = queue.get()

      # check four cardinal neighbors
      for i in range(coord_r-1, coord_r+2):
        for j in range(coord_c-1, coord_c+2):
          if self._isInMap(i, j) and (i == coord_r or j == coord_c):
            # if empty space and not checked yet
            if self.map[i][j] == 0 and region[i][j] == 0:
              # add to region and put in queue
              region[i][j] = 1
              queue.put((i, j))
              size += 1

    return region, size

  # returns the largest contiguous region with a tile in the leftmost column
  def biggestLeftRegion(self):
    maxSize = 0
    maxRegion = []
    for row in range(self.rows):
      region, size = self._getRegion(row, 0)

      if size > maxSize:
        maxSize = size
        maxRegion = region

    # no region available, just generate random open spot
    if maxSize == 0:
      randomRow = random.randint(1, self.rows - 1)
      self.map[randomRow][0] = 0

      maxRegion = [[0 for i in range(self.cols)] for j in range(self.rows)]
      maxRegion[randomRow][0] = 1

    return maxRegion

  # returns the largest contiguous region with a tile in the rightmost column
  def biggestRightRegion(self):
    maxSize = 0
    maxRegion = []
    for row in range(self.rows):
      region, size = self._getRegion(row, self.cols-1)

      if size > maxSize:
        maxSize = size
        maxRegion = region

    # no region available, just generate random open spot
    if maxSize == 0:
      randomRow = random.randint(1, self.rows - 1)
      self.map[randomRow][self.cols - 1] = 0

      maxRegion = [[0 for i in range(self.cols)] for j in range(self.rows)]
      maxRegion[randomRow][self.cols - 1] = 1

    return maxRegion

  def regionsAreConnected(self, regionA, regionB):
    for r in range(len(regionA)):
      for c in range(len(regionA[0])):
        if regionA[r][c] != regionB[r][c]:
          return False

        # if they share any common spaces, they're connected
        elif regionA[r][c] == 1 and regionB[r][c] == 1:
          return True

    return False

  def connectRegions(self, regionA, regionB):
    coords_cleared = []

    if self.regionsAreConnected(regionA, regionB):
      return coords_cleared

    print("Connecting separate regions")
    rightmostA = (-1, -1)
    leftmostB = (-1, self.cols - 1)

    for r in range(self.rows):
      for c in range(self.cols):
        if regionA[r][c] == 1 and c > rightmostA[1]:
          rightmostA = (r, c)
        if regionB[r][c] == 1 and c < leftmostB[1]:
          leftmostB = (r, c)

    lrchange = 0
    udchange = 0
    if rightmostA[1] < leftmostB[1]:
      lrchange = 1
    elif rightmostA[1] > leftmostB[1]:
      lrchange = -1
    if rightmostA[0] < leftmostB[0]:
      udchange = 1
    elif rightmostA[0] > leftmostB[0]:
      udchange = -1

    rmar = rightmostA[0]
    rmac = rightmostA[1]
    lmbr = leftmostB[0]
    lmbc = leftmostB[1]
    for count in range(1, abs(rmac-lmbc)+1):
      coords_cleared.append((rmar, rmac + count * lrchange))
      self.map[rmar][rmac+count * lrchange] = 0

    for count in range(1, abs(rmar-lmbr)+1):
      coords_cleared.append((rmar + count * udchange, rmac + (lmbc - rmac)))
      self.map[rmar+count*udchange][rmac+(lmbc-rmac)] = 0

    return coords_cleared

  # returns a path between all points in the list points using A*
  def getPath(self, points):
    num_points = len(points)
    if num_points < 2:
      raise Exception("Path needs at least two points")
    
    # check if any points aren't empty
    for point in points:
      if self.map[point[0]][point[1]] == 1:
        raise Exception("The point (%d, %d) is a wall" % (point[0], point[1]))

    overall_path = []
    for n in range(num_points - 1):
      overall_path.append(points[n])

      # generate path between this point and the next one in the list
      a_star = AStarSearch(self.map)
      intermediate_path = a_star(points[n], points[n+1])
      
      # add to the overall path
      if n > 0:
        intermediate_path.pop(0)
      overall_path.extend(intermediate_path)

    return overall_path

  def _jackalMapFromObstacleMap(self, kernel_size):
    output_size = (self.ob_rows - kernel_size + 1, self.ob_cols - kernel_size + 1)
    jackal_map = [[0 for i in range(output_size[1])] for j in range(output_size[0])]
    
    for r in range(0, self.ob_rows - kernel_size + 1):
      for c in range(0, self.ob_cols - kernel_size + 1):
        if not self._kernelWindowIsOpen(kernel_size, r, c):
          jackal_map[r][c] = 1

    return jackal_map

  def _kernelWindowIsOpen(self, kernel_size, r, c):
    for r_kernel in range(r, r + kernel_size):
      for c_kernel in range(c, c + kernel_size):
        if self.ob_map[r_kernel][c_kernel] == 1:
          return False

    return True

  def _isInMap(self, r, c):
    return r >= 0 and r < self.rows and c >= 0 and c < self.cols

  def getMap(self):
    return self.map

class DifficultyMetrics:
  def __init__(self, map):
    self.map = map
    self.rows = len(map)
    self.cols = len(map[0])

  def density(self, radius):
    dens = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        if self.map[r][c] == 0:
          dens[r][c] = self._densityOfTile(r, c, radius)
        else:
          dens[r][c] = (radius * 2) ** 2

    return dens

  def closestWall(self):
    plt.imshow(self.map, cmap='binary', interpolation='nearest')
    plt.show()
    dists = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        dists[r][c] = self._nearest_obs(r, c)

    return dists

  def avgVisibility(self):
    vis = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        vis[r][c] = self._avgVisCell(r, c)

    return vis

  # calculates the number of changes betweeen open & wall
  # in its field of view (along 16 axes)
  def dispersion(self, radius):
    disp = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        disp[r][c] = self._cellDispersion(r, c, radius)

    return disp

  def axis_width(self, axis):
    width = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        width[r][c] = self._distance(r, c, axis)

    return width

  def _distance(self, r, c, axis):
    if self.map[r][c] == 1:
      return -1
    
    reverse_axis = (axis[0] * -1, axis[1] * -1)
    dist = 0
    for move in [axis, reverse_axis]:
      r_curr = r
      c_curr = c
      while self.map[r_curr][c_curr] != 1:
        r_curr += move[0]
        c_curr += move[1]

        if r_curr < 0 or r_curr >= self.rows or c_curr < 0 or c_curr >= self.cols:
          break

        if self.map[r_curr][c_curr] != 1:
          dist += 1

    return dist


  def _cellDispersion(self, r, c, radius):
    if self.map[r][c] == 1:
      return -1

    axes_wall = []
    # four cardinal, four diagonal, and one in between each (slope +- 1/2 or 2)
    for move in [(0, 1), (1, 2), (1, 1), (2, 1), (1, 0), (2, -1), (1, -1), (1, -2), (0, -1), (-2, -1), (-1, -1), (-1, -2), (-1, 0), (-2, 1), (-1, 1), (-1, 2)]:
      count = 0
      wall = False
      r_curr = r
      c_curr = c
      while count < radius and not wall:
        r_curr += move[0]
        c_curr += move[1]

        if r_curr < 0 or r_curr >= self.rows or c_curr < 0 or c_curr >= self.cols:
          break

        if self.map[r_curr][c_curr] == 1:
          wall = True

        # count the in-between axes as two steps
        if move[0] == 2 or move[1] == 2:
          count += 2
        else:
          count += 1
      
      if wall:
        axes_wall.append(True)
      else:
        axes_wall.append(False)

    # count the number of changes in this cell's field of view
    change_count = 0
    for i in range(len(axes_wall)-1):
      if axes_wall[i] != axes_wall[i+1]:
        change_count += 1

    if axes_wall[0] != axes_wall[15]:
      change_count += 1

    return change_count


  def _avgVisCell(self, r, c):
    total_vis = 0
    num_axes = 0
    for r_move in [-1, 0, 1]:
      for c_move in [-1, 0, 1]:
        if r_move == 0 and c_move == 0:
          continue

        this_vis = 0
        r_curr = r
        c_curr = c
        wall_found = False
        while not wall_found:
          if r_curr < 0 or r_curr >= self.rows or c_curr < 0 or c_curr >= self.cols:
            break

          if self.map[r_curr][c_curr] == 1:
            wall_found = True
          else:
            this_vis += 1

          r_curr += r_move
          c_curr += c_move
        
        # if ran out of bounds before finding wall, don't count
        if wall_found:
          total_vis += this_vis
          num_axes += 1
    
    return total_vis / num_axes


  def _densityOfTile(self, row, col, radius):
    count = 0
    for r in range(row-radius, row+radius+1):
      for c in range(col-radius, col+radius+1):
        if r >= 0 and r < self.rows and c >= 0 and c < self.cols and (r!=row or c!=col):
          count += self.map[r][c]

    return count   

  # determines how far a given cell is from a wall (non-diagonal)
  def _distToClosestWall(self, r, c, currCount, currBest):
    if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
      return sys.maxint

    if self.map[r][c] == 1:
      return 0

    if currCount >= currBest:
      return sys.maxint

    bestUp = 1 + self._distToClosestWall(r-1, c, currCount+1, currBest)
    if bestUp < currBest:
      currBest = bestUp
    
    bestDown = 1 + self._distToClosestWall(r+1, c, currCount+1, currBest)
    if bestDown < currBest:
      currBest = bestDown
    
    bestLeft = 1 + self._distToClosestWall(r, c-1, currCount+1, currBest)
    if bestLeft < currBest:
      currBest = bestLeft

    bestRight = 1 + self._distToClosestWall(r, c+1, currCount+1, currBest)

    return min(bestUp, bestDown, bestLeft, bestRight)

  def _isInMap(self, r, c):
    return r >= 0 and r < self.rows and c >= 0 and c < self.cols

  # doesn't check diagonals
  def _nearest_obs(self, r, c):
    q = Queue(0)
    # enqueue the four directions
    q.put(self.Wrapper(1, r - 1, c, -1, 0))
    q.put(self.Wrapper(1, r + 1, c, 1, 0))
    q.put(self.Wrapper(1, r, c - 1, 0, -1))
    q.put(self.Wrapper(1, r, c + 1, 0, 1))

    while not q.empty():
      point = q.get()
      if self._isInMap(point.r, point.c):
        if self.map[point.r][point.c] == 1:
          return point.dist
        else:
          q.put(self.Wrapper(point.dist + 1, point.r + point.r_change, point.c + point.c_change, point.r_change, point.c_change))
    return self.rows

  # wrapper class for coordinates
  class Wrapper:

    def __init__(self, distance, row, col, row_change, col_change):
      self.dist = distance
      self.r = row
      self.c = col
      self.r_change = row_change
      self.c_change = col_change

class AStarSearch:
  def __init__(self, map):
    self.map = map
    self.map_rows = len(map)
    self.map_cols = len(map[0])

  def __call__(self, start_coord, end_coord):
    # initialize start and end nodes
    start_node = Node(None, start_coord)
    start_node.g = start_node.h = start_node.f = 0
    end_node = Node(None, end_coord)
    end_node.g = end_node.h = end_node.f = 0

    # initialize lists to track nodes we've visited or not
    visited = []
    not_visited = []

    # add start to nodes yet to be processed
    not_visited.append(start_node)

    # while there are nodes to process
    while len(not_visited) > 0:
      # get lowest cost next node
      curr_node = not_visited[0]
      curr_idx = 0
      for idx, node in enumerate(not_visited):
        if node.f < curr_node.f:
          curr_node = node
          curr_idx = idx

      # mark this node as processed
      not_visited.pop(curr_idx)
      visited.append(curr_node)

      # if this node is at end of the path, return
      if curr_node == end_node:
        return self.returnPath(curr_node)

      # limit turns to 45 degrees
      valid_moves_dict = {
        (0, 1): [(-1, 1), (0, 1), (1, 1)],
        (1, 1): [(0, 1), (1, 1), (1, 0)],
        (1, 0): [(1, 1), (1, 0), (1, -1)],
        (1, -1): [(1, 0), (1, -1), (0, -1)],
        (0, -1): [(1, -1), (0, -1), (-1, -1)],
        (-1, -1): [(0, -1), (-1, -1), (-1, 0)],
        (-1, 0): [(-1, -1), (-1, 0), (-1, 1)],
        (-1, 1): [(-1, 0), (-1, 1), (0, 1)]
      }

      valid_moves = []
      if curr_node == start_node:
        # if start node, can go any direction
        valid_moves = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
      else:
        # otherwise, can only go straight or 45 degree turn
        moving_direction = (curr_node.r - curr_node.parent.r, curr_node.c - curr_node.parent.c)
        valid_moves = valid_moves_dict.get(moving_direction)

      # find all valid, walkable neighbors of this node
      children = []
      for move in valid_moves:

        # calculate neighbor position
        child_pos = (curr_node.r + move[0], curr_node.c + move[1])
        
        # if outside the map, not possible
        if child_pos[0] < 0 or child_pos[0] >= self.map_rows or child_pos[1] < 0 or child_pos[1] >= self.map_cols:
          continue

        # if a wall tile, not possible
        if self.map[child_pos[0]][child_pos[1]] == 1:
          continue

        # also not possible to move between diagonal walls
        if move[0] != 0 and move[1] != 0 and self.map[curr_node.r+move[0]][curr_node.c] == 1 and self.map[curr_node.r][curr_node.c+move[1]] == 1:
          continue

        # if neighbor is possible to reach, add to list of neighbors
        child_node = Node(curr_node, child_pos)
        children.append(child_node)


      # loop through all walkable neighbors of this node
      for child in children:

        # if neighbor already visited, not usable
        if child in visited:
          continue

        # calculate f, g, h values
        child.g += 1
        child.h = math.sqrt(((child.r - end_node.r) ** 2) + ((child.c - end_node.c) ** 2))
        child.f = child.g + child.h

        # if this node is already in the unprocessed list
        # with a g-value lower than what we have, don't add it
        if len([i for i in not_visited if child == i and child.g > i.g]) > 0:
          continue

        not_visited.append(child)

  # generate the path from start to end
  def returnPath(self, end_node):
    path = []
    curr_node = end_node
    while curr_node != None:
      path.append((curr_node.r, curr_node.c))
      curr_node = curr_node.parent

    path.reverse()
    return path


class Node:
  def __init__(self, parent, coord):
    self.parent = parent
    self.r = coord[0]
    self.c = coord[1]

    self.g = 0
    self.h = 0
    self.f = 0

  def __eq__(self, other):
    return self.r == other.r and self.c == other.c
 

class Display:
  def __init__(self, map, map_with_path, jackal_map, jackal_map_with_path, density_radius, dispersion_radius):
    self.map = map
    self.map_with_path = map_with_path
    self.jackal_map = jackal_map
    self.jackal_map_with_path = jackal_map_with_path
    self.density_radius = density_radius
    self.dispersion_radius = dispersion_radius
  
    diff = DifficultyMetrics(jackal_map)
    self.metrics = {
      "closestDist": diff.closestWall(),
      "density": diff.density(density_radius),
      "avgVis": diff.avgVisibility(),
      "dispersion": diff.dispersion(dispersion_radius),
      "leftright_width": diff.axis_width((0, 1)),
      "updown_width": diff.axis_width((1, 0)),
      "pos_diag_width": diff.axis_width((-1, 1)),
      "neg_diag_width": diff.axis_width((1, 1)),
    }

  def __call__(self):
    fig, ax = plt.subplots(3, 3)
    
    

    # map and path
    map_plot = ax[0][0].imshow(self.map_with_path, cmap='Greys', interpolation='nearest')
    map_plot.axes.get_xaxis().set_visible(False)
    map_plot.axes.get_yaxis().set_visible(False)
    ax[0][0].set_title("Map and A* path")

    # closest wall distance
    dists = self.metrics.get("closestDist")
    dist_plot = ax[0][1].imshow(dists, cmap='RdYlGn', interpolation='nearest')
    dist_plot.axes.get_xaxis().set_visible(False)
    dist_plot.axes.get_yaxis().set_visible(False)
    ax[0][1].set_title("Distance to \nclosest obstacle")
    dist_cbar = fig.colorbar(dist_plot, ax=ax[0][1], orientation='horizontal')
    dist_cbar.ax.tick_params(labelsize='xx-small')

    # density
    densities = self.metrics.get("density")
    density_plot = ax[0][2].imshow(densities, cmap='binary', interpolation='nearest')
    density_plot.axes.get_xaxis().set_visible(False)
    density_plot.axes.get_yaxis().set_visible(False)
    ax[0][2].set_title("%d-square radius density" % self.density_radius)
    dens_cbar = fig.colorbar(density_plot, ax=ax[0][2], orientation='horizontal')
    dens_cbar.ax.tick_params(labelsize='xx-small')

    # average visibility
    avgVis = self.metrics.get("avgVis")
    avgVis_plot = ax[1][0].imshow(avgVis, cmap='RdYlGn', interpolation='nearest')
    avgVis_plot.axes.get_xaxis().set_visible(False)
    avgVis_plot.axes.get_yaxis().set_visible(False)
    ax[1][0].set_title("Average visibility")
    avgVis_cbar = fig.colorbar(avgVis_plot, ax=ax[1][0], orientation='horizontal')
    avgVis_cbar.ax.tick_params(labelsize='xx-small')
    
    # dispersion
    dispersion = self.metrics.get("dispersion")
    disp_plot = ax[1][1].imshow(dispersion, cmap='RdYlGn', interpolation='nearest')
    disp_plot.axes.get_xaxis().set_visible(False)
    disp_plot.axes.get_yaxis().set_visible(False)
    ax[1][1].set_title("%d-square radius dispersion" % self.dispersion_radius)
    disp_cbar = fig.colorbar(disp_plot, ax=ax[1][1], orientation='horizontal')
    disp_cbar.ax.tick_params(labelsize='xx-small')

    # jackal's navigable map, low-res
    jmap_plot = ax[2][0].imshow(self.jackal_map_with_path, cmap='Greys', interpolation='nearest')
    jmap_plot.axes.get_xaxis().set_visible(False)
    jmap_plot.axes.get_yaxis().set_visible(False)
    ax[2][0].set_title("Jackal navigable map")

    plt.delaxes(ax[1][2])
    plt.axis('off')
    plt.show()


class Input:
  def __init__(self):
    self.root = tk.Tk(className="Parameters")

    tk.Label(self.root, text="Seed").grid(row=0)
    tk.Label(self.root, text="Smoothing iterations").grid(row=1)
    tk.Label(self.root, text="Fill percentage (0 to 1)").grid(row=2)
    tk.Label(self.root, text="Rows").grid(row=3, column=0)
    tk.Label(self.root, text="Cols").grid(row=3, column=2)

    self.seed = tk.Entry(self.root)
    self.seed.grid(row=0, column=1)

    self.smoothIter = tk.Entry(self.root)
    self.smoothIter.insert(0, "4")
    self.smoothIter.grid(row=1, column=1)

    self.fillPct = tk.Entry(self.root)
    self.fillPct.insert(0, "0.35")
    self.fillPct.grid(row=2, column=1)

    self.rows = tk.Entry(self.root)
    self.rows.insert(0, "25")
    self.rows.grid(row=3, column=1)

    self.cols = tk.Entry(self.root)
    self.cols.insert(0, "25")
    self.cols.grid(row=3, column=3)

    self.showMetrics = tk.IntVar()
    self.showMetrics.set(True)
    showMetricsBox = tk.Checkbutton(self.root, text="Show metrics", var=self.showMetrics)
    showMetricsBox.grid(row=4, column=1)

    tk.Button(self.root, text='Run', command=self.get_input).grid(row=5, column=1)

    self.root.mainloop()
  
  def get_input(self):
    self.inputs = {}

    # get seed
    if len(self.seed.get()) == 0:
      self.inputs["seed"] = hash(datetime.datetime.now())
    else:
      try:
        self.inputs["seed"] = int(self.seed.get())
      except:
        self.inputs["seed"] = hash(self.seed.get())

    # get number of smoothing iterations
    default_smooth_iter = 4
    try:
      self.inputs["smoothIter"] = int(self.smoothIter.get())
    except:
      self.inputs["smoothIter"] = default_smooth_iter

    # get random fill percentage
    default_fill_pct = 0.35
    try:
      self.inputs["fillPct"] = float(self.fillPct.get())
    except:
      self.inputs["fillPct"] = default_fill_pct

    # get number of rows
    default_rows = 25
    try:
      self.inputs["rows"] = int(self.rows.get())
    except:
      self.inputs["rows"] = default_rows

    # get number of columns
    default_cols = 25
    try:
      self.inputs["cols"] = int(self.cols.get())
    except:
      self.inputs["rows"] = default_cols

    # get show metrics value
    default_show_metrics = 1
    try:
      self.inputs["showMetrics"] = self.showMetrics.get()
    except:
      self.inputs["showMetrics"] = default_show_metrics
      
    self.root.destroy()


def main(iteration=0):

    # dirName = "~/jackal_ws/src/jackal_simulator/jackal_gazebo/worlds/"

    world_file = "world_" + str(iteration) + ".world"
    grid_file = "grid_" + str(iteration) + ".npy"
    path_file = "path_" + str(iteration) + ".npy"

    # get user parameters, if provided
    # inputWindow = Input()
    # inputDict = inputWindow.inputs

    inputDict = { "seed" : hash(datetime.datetime.now()),
                  "smoothIter": 4,
                  "fillPct" : 0.35,
                  "rows" : 25,
                  "cols" : 25,
                  "showMetrics" : 0 }

    # create 25x25 world generator and run smoothing iterations
    print("Seed: %d" % inputDict["seed"])
    obMapGen = ObstacleMap(inputDict["rows"], inputDict["cols"], inputDict["fillPct"], inputDict["seed"], inputDict["smoothIter"])
    obMapGen()

    # get map from the obstacle map generator
    obstacle_map = obMapGen.getMap()
    
    # generate jackal's map from the obstacle map & ensure connectivity
    jMapGen = JackalMap(obstacle_map, def_kernel_size)
    startRegion = jMapGen.biggestLeftRegion()
    endRegion = jMapGen.biggestRightRegion()
    

    cleared_coords = jMapGen.connectRegions(startRegion, endRegion)

    # get the final jackal map and update the obstacle map
    jackal_map = jMapGen.getMap()
    obstacle_map = obMapGen.updateObstacleMap(cleared_coords, def_kernel_size)

    # write map to .world file
    writer = WorldWriter(world_file, obstacle_map, cyl_radius=0.075)
    writer()

    """ Generate random points to demonstrate path """
    left_open = []
    right_open = []
    for r in range(len(jackal_map)):
      if startRegion[r][0] == 1:
        left_open.append(r)
      if endRegion[r][len(jackal_map[0])-1] == 1:
        right_open.append(r)
    left_coord = left_open[random.randint(0, len(left_open)-1)]
    right_coord = right_open[random.randint(0, len(right_open)-1)]
    """ End random point selection """

    
    # generate path, if possible
    path = []
    print("Points: (%d, 0), (%d, %d)" % (left_coord, right_coord, len(jackal_map[0])-1))
    path = jMapGen.getPath([(left_coord, 0), (right_coord, len(jackal_map[0])-1)])
    print("Found path!")

    # put paths into matrices to display them
    obstacle_map_with_path = [[obstacle_map[j][i] for i in range(len(obstacle_map[0]))] for j in range(len(obstacle_map))]
    jackal_map_with_path = [[jackal_map[j][i] for i in range(len(jackal_map[0]))] for j in range(len(jackal_map))]
    for r, c in path:
      # update jackal-space path display
      jackal_map_with_path[r][c] = 0.35

      # update obstacle-space path display
      for r_kernel in range(r, r + def_kernel_size):
        for c_kernel in range(c, c + def_kernel_size):
          obstacle_map_with_path[r_kernel][c_kernel] = 0.35
    jackal_map_with_path[left_coord][0] = 0.65
    jackal_map_with_path[right_coord][len(jackal_map[0])-1] = 0.65
    obstacle_map_with_path[left_coord][0] = 0.65
    obstacle_map_with_path[right_coord][len(obstacle_map[0])-1] = 0.65

    np_arr = np.asarray(obstacle_map_with_path)
    np.save(grid_file, np_arr)

    """
    # display world and heatmap of distances
    if inputDict["showMetrics"]:
      display = Display(obstacle_map, obstacle_map_with_path, jackal_map, jackal_map_with_path, density_radius=3, dispersion_radius=3)
      display()

    # only show the map itself
    else:
      plt.imshow(obstacle_map_with_path, cmap='Greys', interpolation='nearest')
      plt.show()
    """    

if __name__ == "__main__":
    main()
        elif self._tileNeighbors(r, c) < 2:
          newmap[r][c] = 0

    self.map = newmap

  def _tileNeighbors(self, r, c):
    count = 0
    for i in range(r - 1, r + 2):
      for j in range(c - 1, c + 2):
        if self._isInMap(i, j):
          if i != r or j != c:
            count += self.map[i][j]

        # if on the top or bottom, add to wall neighbors
        elif i < 0 or i >= self.rows:
          count += 1
    
    return count

  def _isInMap(self, r, c):
    return r >= 0 and r < self.rows and c >= 0 and c < self.cols

  # update the obstacle map given the jackal-space
  # coordinates that were cleared to ensure connectivity
  def updateObstacleMap(self, cleared_coords, kernel_size):
    for coord in cleared_coords:
      for r in range(coord[0], coord[0] + kernel_size):
        for c in range(coord[1], coord[1] + kernel_size):
          self.map[r][c] = 0

    return self.map

  def getMap(self):
    return self.map

class JackalMap:
  def __init__(self, ob_map, kernel_size):
    self.ob_map = ob_map
    self.ob_rows = len(ob_map)
    self.ob_cols = len(ob_map[0])

    self.kernel_size = kernel_size
    self.map = self._jackalMapFromObstacleMap(self.kernel_size)
    self.rows = len(self.map)
    self.cols = len(self.map[0])

  # use flood-fill algorithm to find the open region including (r, c)
  def _getRegion(self, r, c):
    queue = Queue.Queue(maxsize=0)
    region = [[0 for i in range(self.cols)] for j in range(self.rows)]
    size = 0

    if self.map[r][c] == 0:
      queue.put((r, c))
      region[r][c] = 1
      size += 1

    while not queue.empty():
      coord_r, coord_c = queue.get()

      # check four cardinal neighbors
      for i in range(coord_r-1, coord_r+2):
        for j in range(coord_c-1, coord_c+2):
          if self._isInMap(i, j) and (i == coord_r or j == coord_c):
            # if empty space and not checked yet
            if self.map[i][j] == 0 and region[i][j] == 0:
              # add to region and put in queue
              region[i][j] = 1
              queue.put((i, j))
              size += 1

    return region, size

  # returns the largest contiguous region with a tile in the leftmost column
  def biggestLeftRegion(self):
    maxSize = 0
    maxRegion = []
    for row in range(self.rows):
      region, size = self._getRegion(row, 0)

      if size > maxSize:
        maxSize = size
        maxRegion = region

    return maxRegion

  # returns the largest contiguous region with a tile in the rightmost column
  def biggestRightRegion(self):
    maxSize = 0
    maxRegion = []
    for row in range(self.rows):
      region, size = self._getRegion(row, self.cols-1)

      if size > maxSize:
        maxSize = size
        maxRegion = region

    return maxRegion

  def regionsAreConnected(self, regionA, regionB):
    for r in range(len(regionA)):
      for c in range(len(regionA[0])):
        if regionA[r][c] != regionB[r][c]:
          return False

        # if they share any common spaces, they're connected
        elif regionA[r][c] == 1 and regionB[r][c] == 1:
          return True

    return False

  def connectRegions(self, regionA, regionB):
    coords_cleared = []

    if self.regionsAreConnected(regionA, regionB):
      return coords_cleared

    print("Connecting separate regions")
    rightmostA = (-1, -1)
    leftmostB = (-1, self.cols - 1)

    for r in range(self.rows):
      for c in range(self.cols):
        if regionA[r][c] == 1 and c > rightmostA[1]:
          rightmostA = (r, c)
        if regionB[r][c] == 1 and c < leftmostB[1]:
          leftmostB = (r, c)

    lrchange = 0
    udchange = 0
    if rightmostA[1] < leftmostB[1]:
      lrchange = 1
    elif rightmostA[1] > leftmostB[1]:
      lrchange = -1
    if rightmostA[0] < leftmostB[0]:
      udchange = 1
    elif rightmostA[0] > leftmostB[0]:
      udchange = -1

    rmar = rightmostA[0]
    rmac = rightmostA[1]
    lmbr = leftmostB[0]
    lmbc = leftmostB[1]
    for count in range(1, abs(rmac-lmbc)+1):
      coords_cleared.append((rmar, rmac + count * lrchange))
      self.map[rmar][rmac+count * lrchange] = 0

    for count in range(1, abs(rmar-lmbr)+1):
      coords_cleared.append((rmar + count * udchange, rmac + (lmbc - rmac)))
      self.map[rmar+count*udchange][rmac+(lmbc-rmac)] = 0

    return coords_cleared

  # returns a path between all points in the list points using A*
  def getPath(self, points):
    num_points = len(points)
    if num_points < 2:
      raise Exception("Path needs at least two points")
    
    # check if any points aren't empty
    for point in points:
      if self.map[point[0]][point[1]] == 1:
        raise Exception("The point (%d, %d) is a wall" % (point[0], point[1]))

    overall_path = []
    for n in range(num_points - 1):
      overall_path.append(points[n])

      # generate path between this point and the next one in the list
      a_star = AStarSearch(self.map)
      intermediate_path = a_star(points[n], points[n+1])
      
      # add to the overall path
      if n > 0:
        intermediate_path.pop(0)
      overall_path.extend(intermediate_path)

    return overall_path

  def _jackalMapFromObstacleMap(self, kernel_size):
    output_size = (self.ob_rows - kernel_size + 1, self.ob_cols - kernel_size + 1)
    jackal_map = [[0 for i in range(output_size[1])] for j in range(output_size[0])]
    
    for r in range(0, self.ob_rows - kernel_size + 1):
      for c in range(0, self.ob_cols - kernel_size + 1):
        if not self._kernelWindowIsOpen(kernel_size, r, c):
          jackal_map[r][c] = 1

    return jackal_map

  def _kernelWindowIsOpen(self, kernel_size, r, c):
    for r_kernel in range(r, r + kernel_size):
      for c_kernel in range(c, c + kernel_size):
        if self.ob_map[r_kernel][c_kernel] == 1:
          return False

    return True

  def _isInMap(self, r, c):
    return r >= 0 and r < self.rows and c >= 0 and c < self.cols

  def getMap(self):
    return self.map

class DifficultyMetrics:
  def __init__(self, map):
    self.map = map
    self.rows = len(map)
    self.cols = len(map[0])

  def density(self, radius):
    dens = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        if self.map[r][c] == 0:
          dens[r][c] = self._densityOfTile(r, c, radius)
        else:
          dens[r][c] = (radius * 2) ** 2

    return dens

  def closestWall(self):
    dists = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        dists[r][c] = self._distToClosestWall(r, c, 0, sys.maxint)

    return dists

  def avgVisibility(self):
    vis = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        vis[r][c] = self._avgVisCell(r, c)

    return vis

  # calculates the number of changes betweeen open & wall
  # in its field of view (along 16 axes)
  def dispersion(self, radius):
    disp = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        disp[r][c] = self._cellDispersion(r, c, radius)

    return disp

  def axis_width(self, axis):
    width = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        width[r][c] = self._distance(r, c, axis)

    return width

  def _distance(self, r, c, axis):
    if self.map[r][c] == 1:
      return -1
    
    reverse_axis = (axis[0] * -1, axis[1] * -1)
    dist = 0
    for move in [axis, reverse_axis]:
      r_curr = r
      c_curr = c
      while self.map[r_curr][c_curr] != 1:
        r_curr += move[0]
        c_curr += move[1]

        if r_curr < 0 or r_curr >= self.rows or c_curr < 0 or c_curr >= self.cols:
          break

        if self.map[r_curr][c_curr] != 1:
          dist += 1

    return dist


  def _cellDispersion(self, r, c, radius):
    if self.map[r][c] == 1:
      return -1

    axes_wall = []
    # four cardinal, four diagonal, and one in between each (slope +- 1/2 or 2)
    for move in [(0, 1), (1, 2), (1, 1), (2, 1), (1, 0), (2, -1), (1, -1), (1, -2), (0, -1), (-2, -1), (-1, -1), (-1, -2), (-1, 0), (-2, 1), (-1, 1), (-1, 2)]:
      count = 0
      wall = False
      r_curr = r
      c_curr = c
      while count < radius and not wall:
        r_curr += move[0]
        c_curr += move[1]

        if r_curr < 0 or r_curr >= self.rows or c_curr < 0 or c_curr >= self.cols:
          break

        if self.map[r_curr][c_curr] == 1:
          wall = True

        # count the in-between axes as two steps
        if move[0] == 2 or move[1] == 2:
          count += 2
        else:
          count += 1
      
      if wall:
        axes_wall.append(True)
      else:
        axes_wall.append(False)

    # count the number of changes in this cell's field of view
    change_count = 0
    for i in range(len(axes_wall)-1):
      if axes_wall[i] != axes_wall[i+1]:
        change_count += 1

    if axes_wall[0] != axes_wall[15]:
      change_count += 1

    return change_count


  def _avgVisCell(self, r, c):
    total_vis = 0
    num_axes = 0
    for r_move in [-1, 0, 1]:
      for c_move in [-1, 0, 1]:
        if r_move == 0 and c_move == 0:
          continue

        this_vis = 0
        r_curr = r
        c_curr = c
        wall_found = False
        while not wall_found:
          if r_curr < 0 or r_curr >= self.rows or c_curr < 0 or c_curr >= self.cols:
            break

          if self.map[r_curr][c_curr] == 1:
            wall_found = True
          else:
            this_vis += 1

          r_curr += r_move
          c_curr += c_move
        
        # if ran out of bounds before finding wall, don't count
        if wall_found:
          total_vis += this_vis
          num_axes += 1
    
    return total_vis / num_axes


  def _densityOfTile(self, row, col, radius):
    count = 0
    for r in range(row-radius, row+radius+1):
      for c in range(col-radius, col+radius+1):
        if r >= 0 and r < self.rows and c >= 0 and c < self.cols and (r!=row or c!=col):
          count += self.map[r][c]

    return count   

  # determines how far a given cell is from a wall (non-diagonal)
  def _distToClosestWall(self, r, c, currCount, currBest):
    if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
      return sys.maxint

    if self.map[r][c] == 1:
      return 0

    if currCount >= currBest:
      return sys.maxint

    bestUp = 1 + self._distToClosestWall(r-1, c, currCount+1, currBest)
    if bestUp < currBest:
      currBest = bestUp
    
    bestDown = 1 + self._distToClosestWall(r+1, c, currCount+1, currBest)
    if bestDown < currBest:
      currBest = bestDown
    
    bestLeft = 1 + self._distToClosestWall(r, c-1, currCount+1, currBest)
    if bestLeft < currBest:
      currBest = bestLeft

    bestRight = 1 + self._distToClosestWall(r, c+1, currCount+1, currBest)

    return min(bestUp, bestDown, bestLeft, bestRight)


class AStarSearch:
  def __init__(self, map):
    self.map = map
    self.map_rows = len(map)
    self.map_cols = len(map[0])

  def __call__(self, start_coord, end_coord):
    # initialize start and end nodes
    start_node = Node(None, start_coord)
    start_node.g = start_node.h = start_node.f = 0
    end_node = Node(None, end_coord)
    end_node.g = end_node.h = end_node.f = 0

    # initialize lists to track nodes we've visited or not
    visited = []
    not_visited = []

    # add start to nodes yet to be processed
    not_visited.append(start_node)

    # while there are nodes to process
    while len(not_visited) > 0:
      # get lowest cost next node
      curr_node = not_visited[0]
      curr_idx = 0
      for idx, node in enumerate(not_visited):
        if node.f < curr_node.f:
          curr_node = node
          curr_idx = idx

      # mark this node as processed
      not_visited.pop(curr_idx)
      visited.append(curr_node)

      # if this node is at end of the path, return
      if curr_node == end_node:
        return self.returnPath(curr_node)

      # limit turns to 45 degrees
      valid_moves_dict = {
        (0, 1): [(-1, 1), (0, 1), (1, 1)],
        (1, 1): [(0, 1), (1, 1), (1, 0)],
        (1, 0): [(1, 1), (1, 0), (1, -1)],
        (1, -1): [(1, 0), (1, -1), (0, -1)],
        (0, -1): [(1, -1), (0, -1), (-1, -1)],
        (-1, -1): [(0, -1), (-1, -1), (-1, 0)],
        (-1, 0): [(-1, -1), (-1, 0), (-1, 1)],
        (-1, 1): [(-1, 0), (-1, 1), (0, 1)]
      }

      valid_moves = []
      if curr_node == start_node:
        # if start node, can go any direction
        valid_moves = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
      else:
        # otherwise, can only go straight or 45 degree turn
        moving_direction = (curr_node.r - curr_node.parent.r, curr_node.c - curr_node.parent.c)
        valid_moves = valid_moves_dict.get(moving_direction)

      # find all valid, walkable neighbors of this node
      children = []
      for move in valid_moves:

        # calculate neighbor position
        child_pos = (curr_node.r + move[0], curr_node.c + move[1])
        
        # if outside the map, not possible
        if child_pos[0] < 0 or child_pos[0] >= self.map_rows or child_pos[1] < 0 or child_pos[1] >= self.map_cols:
          continue

        # if a wall tile, not possible
        if self.map[child_pos[0]][child_pos[1]] == 1:
          continue

        # also not possible to move between diagonal walls
        if move[0] != 0 and move[1] != 0 and self.map[curr_node.r+move[0]][curr_node.c] == 1 and self.map[curr_node.r][curr_node.c+move[1]] == 1:
          continue

        # if neighbor is possible to reach, add to list of neighbors
        child_node = Node(curr_node, child_pos)
        children.append(child_node)


      # loop through all walkable neighbors of this node
      for child in children:

        # if neighbor already visited, not usable
        if child in visited:
          continue

        # calculate f, g, h values
        child.g += 1
        child.h = math.sqrt(((child.r - end_node.r) ** 2) + ((child.c - end_node.c) ** 2))
        child.f = child.g + child.h

        # if this node is already in the unprocessed list
        # with a g-value lower than what we have, don't add it
        if len([i for i in not_visited if child == i and child.g > i.g]) > 0:
          continue

        not_visited.append(child)

  # generate the path from start to end
  def returnPath(self, end_node):
    path = []
    curr_node = end_node
    while curr_node != None:
      path.append((curr_node.r, curr_node.c))
      curr_node = curr_node.parent

    path.reverse()
    return path


class Node:
  def __init__(self, parent, coord):
    self.parent = parent
    self.r = coord[0]
    self.c = coord[1]

    self.g = 0
    self.h = 0
    self.f = 0

  def __eq__(self, other):
    return self.r == other.r and self.c == other.c
 

class Display:
  def __init__(self, map, map_with_path, jackal_map, jackal_map_with_path, density_radius, dispersion_radius):
    self.map = map
    self.map_with_path = map_with_path
    self.jackal_map = jackal_map
    self.jackal_map_with_path = jackal_map_with_path
    self.density_radius = density_radius
    self.dispersion_radius = dispersion_radius
  
    diff = DifficultyMetrics(jackal_map)
    self.metrics = {
      "closestDist": diff.closestWall(),
      "density": diff.density(density_radius),
      "avgVis": diff.avgVisibility(),
      "dispersion": diff.dispersion(dispersion_radius),
      "leftright_width": diff.axis_width((0, 1)),
      "updown_width": diff.axis_width((1, 0)),
      "pos_diag_width": diff.axis_width((-1, 1)),
      "neg_diag_width": diff.axis_width((1, 1)),
    }

  def __call__(self):
    fig, ax = plt.subplots(3, 3)
    
    

    # map and path
    map_plot = ax[0][0].imshow(self.map_with_path, cmap='Greys', interpolation='nearest')
    map_plot.axes.get_xaxis().set_visible(False)
    map_plot.axes.get_yaxis().set_visible(False)
    ax[0][0].set_title("Map and A* path")

    # closest wall distance
    dists = self.metrics.get("closestDist")
    dist_plot = ax[0][1].imshow(dists, cmap='RdYlGn', interpolation='nearest')
    dist_plot.axes.get_xaxis().set_visible(False)
    dist_plot.axes.get_yaxis().set_visible(False)
    ax[0][1].set_title("Distance to \nclosest obstacle")
    dist_cbar = fig.colorbar(dist_plot, ax=ax[0][1], orientation='horizontal')
    dist_cbar.ax.tick_params(labelsize='xx-small')

    # density
    densities = self.metrics.get("density")
    density_plot = ax[0][2].imshow(densities, cmap='binary', interpolation='nearest')
    density_plot.axes.get_xaxis().set_visible(False)
    density_plot.axes.get_yaxis().set_visible(False)
    ax[0][2].set_title("%d-square radius density" % self.density_radius)
    dens_cbar = fig.colorbar(density_plot, ax=ax[0][2], orientation='horizontal')
    dens_cbar.ax.tick_params(labelsize='xx-small')

    # average visibility
    avgVis = self.metrics.get("avgVis")
    avgVis_plot = ax[1][0].imshow(avgVis, cmap='RdYlGn', interpolation='nearest')
    avgVis_plot.axes.get_xaxis().set_visible(False)
    avgVis_plot.axes.get_yaxis().set_visible(False)
    ax[1][0].set_title("Average visibility")
    avgVis_cbar = fig.colorbar(avgVis_plot, ax=ax[1][0], orientation='horizontal')
    avgVis_cbar.ax.tick_params(labelsize='xx-small')
    
    # dispersion
    dispersion = self.metrics.get("dispersion")
    disp_plot = ax[1][1].imshow(dispersion, cmap='RdYlGn', interpolation='nearest')
    disp_plot.axes.get_xaxis().set_visible(False)
    disp_plot.axes.get_yaxis().set_visible(False)
    ax[1][1].set_title("%d-square radius dispersion" % self.dispersion_radius)
    disp_cbar = fig.colorbar(disp_plot, ax=ax[1][1], orientation='horizontal')
    disp_cbar.ax.tick_params(labelsize='xx-small')

    # jackal's navigable map, low-res
    jmap_plot = ax[2][0].imshow(self.jackal_map_with_path, cmap='Greys', interpolation='nearest')
    jmap_plot.axes.get_xaxis().set_visible(False)
    jmap_plot.axes.get_yaxis().set_visible(False)
    ax[2][0].set_title("Jackal navigable map")

    plt.delaxes(ax[1][2])
    plt.axis('off')
    plt.show()


class Input:
  def __init__(self):
    self.root = tk.Tk(className="Parameters")

    tk.Label(self.root, text="Seed").grid(row=0)
    tk.Label(self.root, text="Smoothing iterations").grid(row=1)
    tk.Label(self.root, text="Fill percentage (0 to 1)").grid(row=2)
    tk.Label(self.root, text="Rows").grid(row=3, column=0)
    tk.Label(self.root, text="Cols").grid(row=3, column=2)

    self.seed = tk.Entry(self.root)
    self.seed.grid(row=0, column=1)

    self.smoothIter = tk.Entry(self.root)
    self.smoothIter.insert(0, "4")
    self.smoothIter.grid(row=1, column=1)

    self.fillPct = tk.Entry(self.root)
    self.fillPct.insert(0, "0.35")
    self.fillPct.grid(row=2, column=1)

    self.rows = tk.Entry(self.root)
    self.rows.insert(0, "25")
    self.rows.grid(row=3, column=1)

    self.cols = tk.Entry(self.root)
    self.cols.insert(0, "25")
    self.cols.grid(row=3, column=3)

    self.showMetrics = tk.IntVar()
    self.showMetrics.set(True)
    showMetricsBox = tk.Checkbutton(self.root, text="Show metrics", var=self.showMetrics)
    showMetricsBox.grid(row=4, column=1)

    tk.Button(self.root, text='Run', command=self.get_input).grid(row=5, column=1)

    self.root.mainloop()
  
  def get_input(self):
    self.inputs = {}

    # get seed
    if len(self.seed.get()) == 0:
      self.inputs["seed"] = hash(datetime.datetime.now())
    else:
      try:
        self.inputs["seed"] = int(self.seed.get())
      except:
        self.inputs["seed"] = hash(self.seed.get())

    # get number of smoothing iterations
    default_smooth_iter = 4
    try:
      self.inputs["smoothIter"] = int(self.smoothIter.get())
    except:
      self.inputs["smoothIter"] = default_smooth_iter

    # get random fill percentage
    default_fill_pct = 0.35
    try:
      self.inputs["fillPct"] = float(self.fillPct.get())
    except:
      self.inputs["fillPct"] = default_fill_pct

    # get number of rows
    default_rows = 25
    try:
      self.inputs["rows"] = int(self.rows.get())
    except:
      self.inputs["rows"] = default_rows

    # get number of columns
    default_cols = 25
    try:
      self.inputs["cols"] = int(self.cols.get())
    except:
      self.inputs["rows"] = default_cols

    # get show metrics value
    default_show_metrics = 1
    try:
      self.inputs["showMetrics"] = self.showMetrics.get()
    except:
      self.inputs["showMetrics"] = default_show_metrics
      
    self.root.destroy()


def main(iteration=0):

    dirName = "~/jackal_ws/src/jackal_simulator/jackal_gazebo/worlds/"

    world_file = "world_" + str(iteration) + ".world"
    grid_file = "grid_" + str(iteration) + ".npy"
    path_file = "path_" + str(iteration) + ".npy"

    # get user parameters, if provided
    inputWindow = Input()
    inputDict = inputWindow.inputs

    # create 25x25 world generator and run smoothing iterations
    print("Seed: %d" % inputDict["seed"])
    obMapGen = ObstacleMap(inputDict["rows"], inputDict["cols"], inputDict["fillPct"], inputDict["seed"], inputDict["smoothIter"])
    obMapGen()

    # get map from the obstacle map generator
    obstacle_map = obMapGen.getMap()
    
    # generate jackal's map from the obstacle map & ensure connectivity
    jMapGen = JackalMap(obstacle_map, def_kernel_size)
    startRegion = jMapGen.biggestLeftRegion()
    endRegion = jMapGen.biggestRightRegion()
    cleared_coords = jMapGen.connectRegions(startRegion, endRegion)

    # get the final jackal map and update the obstacle map
    jackal_map = jMapGen.getMap()
    obstacle_map = obMapGen.updateObstacleMap(cleared_coords, def_kernel_size)

    # write map to .world file
    writer = WorldWriter(world_file, obstacle_map, cyl_radius=0.075)
    writer()

    """ Generate random points to demonstrate path """
    left_open = []
    right_open = []
    for r in range(len(jackal_map)):
      if startRegion[r][0] == 1:
        left_open.append(r)
      if endRegion[r][len(jackal_map[0])-1] == 1:
        right_open.append(r)
    left_coord = left_open[random.randint(0, len(left_open)-1)]
    right_coord = right_open[random.randint(0, len(right_open)-1)]
    """ End random point selection """

    
    # generate path, if possible
    path = []
    print("Points: (%d, 0), (%d, %d)" % (left_coord, right_coord, len(jackal_map[0])-1))
    path = jMapGen.getPath([(left_coord, 0), (right_coord, len(jackal_map[0])-1)])
    print("Found path!")

    # put paths into matrices to display them
    obstacle_map_with_path = [[obstacle_map[j][i] for i in range(len(obstacle_map[0]))] for j in range(len(obstacle_map))]
    jackal_map_with_path = [[jackal_map[j][i] for i in range(len(jackal_map[0]))] for j in range(len(jackal_map))]
    for r, c in path:
      # update jackal-space path display
      jackal_map_with_path[r][c] = 0.35

      # update obstacle-space path display
      for r_kernel in range(r, r + def_kernel_size):
        for c_kernel in range(c, c + def_kernel_size):
          obstacle_map_with_path[r_kernel][c_kernel] = 0.35
    jackal_map_with_path[left_coord][0] = 0.65
    jackal_map_with_path[right_coord][len(jackal_map[0])-1] = 0.65
    obstacle_map_with_path[left_coord][0] = 0.65
    obstacle_map_with_path[right_coord][len(obstacle_map[0])-1] = 0.65

    np_arr = np.asarray(obstacle_map_with_path)
    np.save(grid_file, np_arr)

    
    # display world and heatmap of distances
    if inputDict["showMetrics"]:
      display = Display(obstacle_map, obstacle_map_with_path, jackal_map, jackal_map_with_path, density_radius=3, dispersion_radius=3)
      display()

    # only show the map itself
    else:
      plt.imshow(obstacle_map_with_path, cmap='Greys', interpolation='nearest')
      plt.show()
    

if __name__ == "__main__":
    main()
          newmap[r][c] = 0

    self.map = newmap

  def _tileNeighbors(self, r, c):
    count = 0
    for i in range(r - 1, r + 2):
      for j in range(c - 1, c + 2):
        if self._isInMap(i, j):
          if i != r or j != c:
            count += self.map[i][j]

        # if on the top or bottom, add to wall neighbors
        elif i < 0 or i >= self.rows:
          count += 1
    
    return count

  def _isInMap(self, r, c):
    return r >= 0 and r < self.rows and c >= 0 and c < self.cols

  # update the obstacle map given the jackal-space
  # coordinates that were cleared to ensure connectivity
  def updateObstacleMap(self, cleared_coords, kernel_size):
    for coord in cleared_coords:
      for r in range(coord[0], coord[0] + kernel_size):
        for c in range(coord[1], coord[1] + kernel_size):
          self.map[r][c] = 0

    return self.map

  def getMap(self):
    return self.map

class JackalMap:
  def __init__(self, ob_map, kernel_size):
    self.ob_map = ob_map
    self.ob_rows = len(ob_map)
    self.ob_cols = len(ob_map[0])

    self.kernel_size = kernel_size
    self.map = self._jackalMapFromObstacleMap(self.kernel_size)
    self.rows = len(self.map)
    self.cols = len(self.map[0])

  # use flood-fill algorithm to find the open region including (r, c)
  def _getRegion(self, r, c):
    queue = Queue.Queue(maxsize=0)
    region = [[0 for i in range(self.cols)] for j in range(self.rows)]
    size = 0

    if self.map[r][c] == 0:
      queue.put((r, c))
      region[r][c] = 1
      size += 1

    while not queue.empty():
      coord_r, coord_c = queue.get()

      # check four cardinal neighbors
      for i in range(coord_r-1, coord_r+2):
        for j in range(coord_c-1, coord_c+2):
          if self._isInMap(i, j) and (i == coord_r or j == coord_c):
            # if empty space and not checked yet
            if self.map[i][j] == 0 and region[i][j] == 0:
              # add to region and put in queue
              region[i][j] = 1
              queue.put((i, j))
              size += 1

    return region, size

  # returns the largest contiguous region with a tile in the leftmost column
  def biggestLeftRegion(self):
    maxSize = 0
    maxRegion = []
    for row in range(self.rows):
      region, size = self._getRegion(row, 0)

      if size > maxSize:
        maxSize = size
        maxRegion = region

    return maxRegion

  # returns the largest contiguous region with a tile in the rightmost column
  def biggestRightRegion(self):
    maxSize = 0
    maxRegion = []
    for row in range(self.rows):
      region, size = self._getRegion(row, self.cols-1)

      if size > maxSize:
        maxSize = size
        maxRegion = region

    return maxRegion

  def regionsAreConnected(self, regionA, regionB):
    for r in range(len(regionA)):
      for c in range(len(regionA[0])):
        if regionA[r][c] != regionB[r][c]:
          return False

        # if they share any common spaces, they're connected
        elif regionA[r][c] == 1 and regionB[r][c] == 1:
          return True

    return False

  def connectRegions(self, regionA, regionB):
    coords_cleared = []

    if self.regionsAreConnected(regionA, regionB):
      return coords_cleared

    print("Connecting separate regions")
    rightmostA = (-1, -1)
    leftmostB = (-1, self.cols - 1)

    for r in range(self.rows):
      for c in range(self.cols):
        if regionA[r][c] == 1 and c > rightmostA[1]:
          rightmostA = (r, c)
        if regionB[r][c] == 1 and c < leftmostB[1]:
          leftmostB = (r, c)

    lrchange = 0
    udchange = 0
    if rightmostA[1] < leftmostB[1]:
      lrchange = 1
    elif rightmostA[1] > leftmostB[1]:
      lrchange = -1
    if rightmostA[0] < leftmostB[0]:
      udchange = 1
    elif rightmostA[0] > leftmostB[0]:
      udchange = -1

    rmar = rightmostA[0]
    rmac = rightmostA[1]
    lmbr = leftmostB[0]
    lmbc = leftmostB[1]
    for count in range(1, abs(rmac-lmbc)+1):
      coords_cleared.append((rmar, rmac + count * lrchange))
      self.map[rmar][rmac+count * lrchange] = 0

    for count in range(1, abs(rmar-lmbr)+1):
      coords_cleared.append((rmar + count * udchange, rmac + (lmbc - rmac)))
      self.map[rmar+count*udchange][rmac+(lmbc-rmac)] = 0

    return coords_cleared

  # returns a path between all points in the list points using A*
  def getPath(self, points):
    num_points = len(points)
    if num_points < 2:
      raise Exception("Path needs at least two points")
    
    # check if any points aren't empty
    for point in points:
      if self.map[point[0]][point[1]] == 1:
        raise Exception("The point (%d, %d) is a wall" % (point[0], point[1]))

    overall_path = []
    for n in range(num_points - 1):
      overall_path.append(points[n])

      # generate path between this point and the next one in the list
      a_star = AStarSearch(self.map)
      intermediate_path = a_star(points[n], points[n+1])
      
      # add to the overall path
      if n > 0:
        intermediate_path.pop(0)
      overall_path.extend(intermediate_path)

    return overall_path

  def _jackalMapFromObstacleMap(self, kernel_size):
    output_size = (self.ob_rows - kernel_size + 1, self.ob_cols - kernel_size + 1)
    jackal_map = [[0 for i in range(output_size[1])] for j in range(output_size[0])]
    
    for r in range(0, self.ob_rows - kernel_size + 1):
      for c in range(0, self.ob_cols - kernel_size + 1):
        if not self._kernelWindowIsOpen(kernel_size, r, c):
          jackal_map[r][c] = 1

    return jackal_map

  def _kernelWindowIsOpen(self, kernel_size, r, c):
    for r_kernel in range(r, r + kernel_size):
      for c_kernel in range(c, c + kernel_size):
        if self.ob_map[r_kernel][c_kernel] == 1:
          return False

    return True

  def _isInMap(self, r, c):
    return r >= 0 and r < self.rows and c >= 0 and c < self.cols

  def getMap(self):
    return self.map

class DifficultyMetrics:
  def __init__(self, map):
    self.map = map
    self.rows = len(map)
    self.cols = len(map[0])

  def density(self, radius):
    dens = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        if self.map[r][c] == 0:
          dens[r][c] = self._densityOfTile(r, c, radius)
        else:
          dens[r][c] = (radius * 2) ** 2

    return dens

  def closestWall(self):
    dists = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        dists[r][c] = self._distToClosestWall(r, c, 0, sys.maxint)

    return dists

  def avgVisibility(self):
    vis = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        vis[r][c] = self._avgVisCell(r, c)

    return vis

  # calculates the number of changes betweeen open & wall
  # in its field of view (along 16 axes)
  def dispersion(self, radius):
    disp = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        disp[r][c] = self._cellDispersion(r, c, radius)

    return disp

  def axis_width(self, axis):
    width = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        width[r][c] = self._distance(r, c, axis)

    return width

  def _distance(self, r, c, axis):
    if self.map[r][c] == 1:
      return -1
    
    reverse_axis = (axis[0] * -1, axis[1] * -1)
    dist = 0
    for move in [axis, reverse_axis]:
      r_curr = r
      c_curr = c
      while self.map[r_curr][c_curr] != 1:
        r_curr += move[0]
        c_curr += move[1]

        if r_curr < 0 or r_curr >= self.rows or c_curr < 0 or c_curr >= self.cols:
          break

        if self.map[r_curr][c_curr] != 1:
          dist += 1

    return dist


  def _cellDispersion(self, r, c, radius):
    if self.map[r][c] == 1:
      return -1

    axes_wall = []
    # four cardinal, four diagonal, and one in between each (slope +- 1/2 or 2)
    for move in [(0, 1), (1, 2), (1, 1), (2, 1), (1, 0), (2, -1), (1, -1), (1, -2), (0, -1), (-2, -1), (-1, -1), (-1, -2), (-1, 0), (-2, 1), (-1, 1), (-1, 2)]:
      count = 0
      wall = False
      r_curr = r
      c_curr = c
      while count < radius and not wall:
        r_curr += move[0]
        c_curr += move[1]

        if r_curr < 0 or r_curr >= self.rows or c_curr < 0 or c_curr >= self.cols:
          break

        if self.map[r_curr][c_curr] == 1:
          wall = True

        # count the in-between axes as two steps
        if move[0] == 2 or move[1] == 2:
          count += 2
        else:
          count += 1
      
      if wall:
        axes_wall.append(True)
      else:
        axes_wall.append(False)

    # count the number of changes in this cell's field of view
    change_count = 0
    for i in range(len(axes_wall)-1):
      if axes_wall[i] != axes_wall[i+1]:
        change_count += 1

    if axes_wall[0] != axes_wall[15]:
      change_count += 1

    return change_count


  def _avgVisCell(self, r, c):
    total_vis = 0
    num_axes = 0
    for r_move in [-1, 0, 1]:
      for c_move in [-1, 0, 1]:
        if r_move == 0 and c_move == 0:
          continue

        this_vis = 0
        r_curr = r
        c_curr = c
        wall_found = False
        while not wall_found:
          if r_curr < 0 or r_curr >= self.rows or c_curr < 0 or c_curr >= self.cols:
            break

          if self.map[r_curr][c_curr] == 1:
            wall_found = True
          else:
            this_vis += 1

          r_curr += r_move
          c_curr += c_move
        
        # if ran out of bounds before finding wall, don't count
        if wall_found:
          total_vis += this_vis
          num_axes += 1
    
    return total_vis / num_axes


  def _densityOfTile(self, row, col, radius):
    count = 0
    for r in range(row-radius, row+radius+1):
      for c in range(col-radius, col+radius+1):
        if r >= 0 and r < self.rows and c >= 0 and c < self.cols and (r!=row or c!=col):
          count += self.map[r][c]

    return count   

  # determines how far a given cell is from a wall (non-diagonal)
  def _distToClosestWall(self, r, c, currCount, currBest):
    if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
      return sys.maxint

    if self.map[r][c] == 1:
      return 0

    if currCount >= currBest:
      return sys.maxint

    bestUp = 1 + self._distToClosestWall(r-1, c, currCount+1, currBest)
    if bestUp < currBest:
      currBest = bestUp
    
    bestDown = 1 + self._distToClosestWall(r+1, c, currCount+1, currBest)
    if bestDown < currBest:
      currBest = bestDown
    
    bestLeft = 1 + self._distToClosestWall(r, c-1, currCount+1, currBest)
    if bestLeft < currBest:
      currBest = bestLeft

    bestRight = 1 + self._distToClosestWall(r, c+1, currCount+1, currBest)

    return min(bestUp, bestDown, bestLeft, bestRight)


class AStarSearch:
  def __init__(self, map):
    self.map = map
    self.map_rows = len(map)
    self.map_cols = len(map[0])

  def __call__(self, start_coord, end_coord):
    # initialize start and end nodes
    start_node = Node(None, start_coord)
    start_node.g = start_node.h = start_node.f = 0
    end_node = Node(None, end_coord)
    end_node.g = end_node.h = end_node.f = 0

    # initialize lists to track nodes we've visited or not
    visited = []
    not_visited = []

    # add start to nodes yet to be processed
    not_visited.append(start_node)

    # while there are nodes to process
    while len(not_visited) > 0:
      # get lowest cost next node
      curr_node = not_visited[0]
      curr_idx = 0
      for idx, node in enumerate(not_visited):
        if node.f < curr_node.f:
          curr_node = node
          curr_idx = idx

      # mark this node as processed
      not_visited.pop(curr_idx)
      visited.append(curr_node)

      # if this node is at end of the path, return
      if curr_node == end_node:
        return self.returnPath(curr_node)

      # limit turns to 45 degrees
      valid_moves_dict = {
        (0, 1): [(-1, 1), (0, 1), (1, 1)],
        (1, 1): [(0, 1), (1, 1), (1, 0)],
        (1, 0): [(1, 1), (1, 0), (1, -1)],
        (1, -1): [(1, 0), (1, -1), (0, -1)],
        (0, -1): [(1, -1), (0, -1), (-1, -1)],
        (-1, -1): [(0, -1), (-1, -1), (-1, 0)],
        (-1, 0): [(-1, -1), (-1, 0), (-1, 1)],
        (-1, 1): [(-1, 0), (-1, 1), (0, 1)]
      }

      valid_moves = []
      if curr_node == start_node:
        # if start node, can go any direction
        valid_moves = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
      else:
        # otherwise, can only go straight or 45 degree turn
        moving_direction = (curr_node.r - curr_node.parent.r, curr_node.c - curr_node.parent.c)
        valid_moves = valid_moves_dict.get(moving_direction)

      # find all valid, walkable neighbors of this node
      children = []
      for move in valid_moves:

        # calculate neighbor position
        child_pos = (curr_node.r + move[0], curr_node.c + move[1])
        
        # if outside the map, not possible
        if child_pos[0] < 0 or child_pos[0] >= self.map_rows or child_pos[1] < 0 or child_pos[1] >= self.map_cols:
          continue

        # if a wall tile, not possible
        if self.map[child_pos[0]][child_pos[1]] == 1:
          continue

        # also not possible to move between diagonal walls
        if move[0] != 0 and move[1] != 0 and self.map[curr_node.r+move[0]][curr_node.c] == 1 and self.map[curr_node.r][curr_node.c+move[1]] == 1:
          continue

        # if neighbor is possible to reach, add to list of neighbors
        child_node = Node(curr_node, child_pos)
        children.append(child_node)


      # loop through all walkable neighbors of this node
      for child in children:

        # if neighbor already visited, not usable
        if child in visited:
          continue

        # calculate f, g, h values
        child.g += 1
        child.h = math.sqrt(((child.r - end_node.r) ** 2) + ((child.c - end_node.c) ** 2))
        child.f = child.g + child.h

        # if this node is already in the unprocessed list
        # with a g-value lower than what we have, don't add it
        if len([i for i in not_visited if child == i and child.g > i.g]) > 0:
          continue

        not_visited.append(child)

  # generate the path from start to end
  def returnPath(self, end_node):
    path = []
    curr_node = end_node
    while curr_node != None:
      path.append((curr_node.r, curr_node.c))
      curr_node = curr_node.parent

    path.reverse()
    return path


class Node:
  def __init__(self, parent, coord):
    self.parent = parent
    self.r = coord[0]
    self.c = coord[1]

    self.g = 0
    self.h = 0
    self.f = 0

  def __eq__(self, other):
    return self.r == other.r and self.c == other.c
 

class Display:
  def __init__(self, map, map_with_path, jackal_map, jackal_map_with_path, density_radius, dispersion_radius):
    self.map = map
    self.map_with_path = map_with_path
    self.jackal_map = jackal_map
    self.jackal_map_with_path = jackal_map_with_path
    self.density_radius = density_radius
    self.dispersion_radius = dispersion_radius
  
    diff = DifficultyMetrics(jackal_map)
    self.metrics = {
      "closestDist": diff.closestWall(),
      "density": diff.density(density_radius),
      "avgVis": diff.avgVisibility(),
      "dispersion": diff.dispersion(dispersion_radius),
      "leftright_width": diff.axis_width((0, 1)),
      "updown_width": diff.axis_width((1, 0)),
      "pos_diag_width": diff.axis_width((-1, 1)),
      "neg_diag_width": diff.axis_width((1, 1)),
    }

  def __call__(self):
    fig, ax = plt.subplots(3, 3)
    
    

    # map and path
    map_plot = ax[0][0].imshow(self.map_with_path, cmap='Greys', interpolation='nearest')
    map_plot.axes.get_xaxis().set_visible(False)
    map_plot.axes.get_yaxis().set_visible(False)
    ax[0][0].set_title("Map and A* path")

    # closest wall distance
    dists = self.metrics.get("closestDist")
    dist_plot = ax[0][1].imshow(dists, cmap='RdYlGn', interpolation='nearest')
    dist_plot.axes.get_xaxis().set_visible(False)
    dist_plot.axes.get_yaxis().set_visible(False)
    ax[0][1].set_title("Distance to \nclosest obstacle")
    dist_cbar = fig.colorbar(dist_plot, ax=ax[0][1], orientation='horizontal')
    dist_cbar.ax.tick_params(labelsize='xx-small')

    # density
    densities = self.metrics.get("density")
    density_plot = ax[0][2].imshow(densities, cmap='binary', interpolation='nearest')
    density_plot.axes.get_xaxis().set_visible(False)
    density_plot.axes.get_yaxis().set_visible(False)
    ax[0][2].set_title("%d-square radius density" % self.density_radius)
    dens_cbar = fig.colorbar(density_plot, ax=ax[0][2], orientation='horizontal')
    dens_cbar.ax.tick_params(labelsize='xx-small')

    # average visibility
    avgVis = self.metrics.get("avgVis")
    avgVis_plot = ax[1][0].imshow(avgVis, cmap='RdYlGn', interpolation='nearest')
    avgVis_plot.axes.get_xaxis().set_visible(False)
    avgVis_plot.axes.get_yaxis().set_visible(False)
    ax[1][0].set_title("Average visibility")
    avgVis_cbar = fig.colorbar(avgVis_plot, ax=ax[1][0], orientation='horizontal')
    avgVis_cbar.ax.tick_params(labelsize='xx-small')
    
    # dispersion
    dispersion = self.metrics.get("dispersion")
    disp_plot = ax[1][1].imshow(dispersion, cmap='RdYlGn', interpolation='nearest')
    disp_plot.axes.get_xaxis().set_visible(False)
    disp_plot.axes.get_yaxis().set_visible(False)
    ax[1][1].set_title("%d-square radius dispersion" % self.dispersion_radius)
    disp_cbar = fig.colorbar(disp_plot, ax=ax[1][1], orientation='horizontal')
    disp_cbar.ax.tick_params(labelsize='xx-small')

    # jackal's navigable map, low-res
    jmap_plot = ax[2][0].imshow(self.jackal_map_with_path, cmap='Greys', interpolation='nearest')
    jmap_plot.axes.get_xaxis().set_visible(False)
    jmap_plot.axes.get_yaxis().set_visible(False)
    ax[2][0].set_title("Jackal navigable map")

    plt.delaxes(ax[1][2])
    plt.axis('off')
    plt.show()


class Input:
  def __init__(self):
    self.root = tk.Tk(className="Parameters")

    tk.Label(self.root, text="Seed").grid(row=0)
    tk.Label(self.root, text="Smoothing iterations").grid(row=1)
    tk.Label(self.root, text="Fill percentage (0 to 1)").grid(row=2)
    tk.Label(self.root, text="Rows").grid(row=3, column=0)
    tk.Label(self.root, text="Cols").grid(row=3, column=2)

    self.seed = tk.Entry(self.root)
    self.seed.grid(row=0, column=1)

    self.smoothIter = tk.Entry(self.root)
    self.smoothIter.insert(0, "4")
    self.smoothIter.grid(row=1, column=1)

    self.fillPct = tk.Entry(self.root)
    self.fillPct.insert(0, "0.35")
    self.fillPct.grid(row=2, column=1)

    self.rows = tk.Entry(self.root)
    self.rows.insert(0, "25")
    self.rows.grid(row=3, column=1)

    self.cols = tk.Entry(self.root)
    self.cols.insert(0, "25")
    self.cols.grid(row=3, column=3)

    self.showMetrics = tk.IntVar()
    self.showMetrics.set(True)
    showMetricsBox = tk.Checkbutton(self.root, text="Show metrics", var=self.showMetrics)
    showMetricsBox.grid(row=4, column=1)

    tk.Button(self.root, text='Run', command=self.get_input).grid(row=5, column=1)

    self.root.mainloop()
  
  def get_input(self):
    self.inputs = {}

    # get seed
    if len(self.seed.get()) == 0:
      self.inputs["seed"] = hash(datetime.datetime.now())
    else:
      try:
        self.inputs["seed"] = int(self.seed.get())
      except:
        self.inputs["seed"] = hash(self.seed.get())

    # get number of smoothing iterations
    default_smooth_iter = 4
    try:
      self.inputs["smoothIter"] = int(self.smoothIter.get())
    except:
      self.inputs["smoothIter"] = default_smooth_iter

    # get random fill percentage
    default_fill_pct = 0.35
    try:
      self.inputs["fillPct"] = float(self.fillPct.get())
    except:
      self.inputs["fillPct"] = default_fill_pct

    # get number of rows
    default_rows = 25
    try:
      self.inputs["rows"] = int(self.rows.get())
    except:
      self.inputs["rows"] = default_rows

    # get number of columns
import random
import sys
import datetime
import Queue
import math
import matplotlib.pyplot as plt
import Tkinter as tk
from world_writer import WorldWriter
import numpy as np

def_kernel_size = 3

class ObstacleMap():
  def __init__(self, rows, cols, randFillPct, seed=None, smoothIter=5):
    self.map = [[0 for i in range(cols)] for j in range(rows)]
    self.rows = rows
    self.cols = cols
    self.randFillPct = randFillPct
    self.seed = seed
    self.smoothIter = smoothIter

  def __call__(self):
    self._randomFill()
    for n in range(self.smoothIter):
      self._smooth()

  def _randomFill(self):
    if self.seed:
      random.seed(self.seed)

    for r in range(self.rows):
      for c in range(self.cols):
        if r == 0 or r == self.rows - 1:
          self.map[r][c] = 1
        else:
          self.map[r][c] = 1 if random.random() < self.randFillPct else 0

  def _smooth(self):
    newmap = [[self.map[r][c] for c in range(self.cols)] for r in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        # if more than 4 filled neighbors, fill this tile
        if self._tileNeighbors(r, c) > 4:
          newmap[r][c] = 1

        # if less than 2 filled neighbors, empty this one
        elif self._tileNeighbors(r, c) < 2:
          newmap[r][c] = 0

    self.map = newmap

  def _tileNeighbors(self, r, c):
    count = 0
    for i in range(r - 1, r + 2):
      for j in range(c - 1, c + 2):
        if self._isInMap(i, j):
          if i != r or j != c:
            count += self.map[i][j]

        # if on the top or bottom, add to wall neighbors
        elif i < 0 or i >= self.rows:
          count += 1
    
    return count

  def _isInMap(self, r, c):
    return r >= 0 and r < self.rows and c >= 0 and c < self.cols

  # update the obstacle map given the jackal-space
  # coordinates that were cleared to ensure connectivity
  def updateObstacleMap(self, cleared_coords, kernel_size):
    for coord in cleared_coords:
      for r in range(coord[0], coord[0] + kernel_size):
        for c in range(coord[1], coord[1] + kernel_size):
          self.map[r][c] = 0

    return self.map

  def getMap(self):
    return self.map

class JackalMap:
  def __init__(self, ob_map, kernel_size):
    self.ob_map = ob_map
    self.ob_rows = len(ob_map)
    self.ob_cols = len(ob_map[0])

    self.kernel_size = kernel_size
    self.map = self._jackalMapFromObstacleMap(self.kernel_size)
    self.rows = len(self.map)
    self.cols = len(self.map[0])

  # use flood-fill algorithm to find the open region including (r, c)
  def _getRegion(self, r, c):
    queue = Queue.Queue(maxsize=0)
    region = [[0 for i in range(self.cols)] for j in range(self.rows)]
    size = 0

    if self.map[r][c] == 0:
      queue.put((r, c))
      region[r][c] = 1
      size += 1

    while not queue.empty():
      coord_r, coord_c = queue.get()

      # check four cardinal neighbors
      for i in range(coord_r-1, coord_r+2):
        for j in range(coord_c-1, coord_c+2):
          if self._isInMap(i, j) and (i == coord_r or j == coord_c):
            # if empty space and not checked yet
            if self.map[i][j] == 0 and region[i][j] == 0:
              # add to region and put in queue
              region[i][j] = 1
              queue.put((i, j))
              size += 1

    return region, size

  # returns the largest contiguous region with a tile in the leftmost column
  def biggestLeftRegion(self):
    maxSize = 0
    maxRegion = []
    for row in range(self.rows):
      region, size = self._getRegion(row, 0)

      if size > maxSize:
        maxSize = size
        maxRegion = region

    return maxRegion

  # returns the largest contiguous region with a tile in the rightmost column
  def biggestRightRegion(self):
    maxSize = 0
    maxRegion = []
    for row in range(self.rows):
      region, size = self._getRegion(row, self.cols-1)

      if size > maxSize:
        maxSize = size
        maxRegion = region

    return maxRegion

  def regionsAreConnected(self, regionA, regionB):
    for r in range(len(regionA)):
      for c in range(len(regionA[0])):
        if regionA[r][c] != regionB[r][c]:
          return False

        # if they share any common spaces, they're connected
        elif regionA[r][c] == 1 and regionB[r][c] == 1:
          return True

    return False

  def connectRegions(self, regionA, regionB):
    coords_cleared = []

    if self.regionsAreConnected(regionA, regionB):
      return coords_cleared

    print("Connecting separate regions")
    rightmostA = (-1, -1)
    leftmostB = (-1, self.cols - 1)

    for r in range(self.rows):
      for c in range(self.cols):
        if regionA[r][c] == 1 and c > rightmostA[1]:
          rightmostA = (r, c)
        if regionB[r][c] == 1 and c < leftmostB[1]:
          leftmostB = (r, c)

    lrchange = 0
    udchange = 0
    if rightmostA[1] < leftmostB[1]:
      lrchange = 1
    elif rightmostA[1] > leftmostB[1]:
      lrchange = -1
    if rightmostA[0] < leftmostB[0]:
      udchange = 1
    elif rightmostA[0] > leftmostB[0]:
      udchange = -1

    rmar = rightmostA[0]
    rmac = rightmostA[1]
    lmbr = leftmostB[0]
    lmbc = leftmostB[1]
    for count in range(1, abs(rmac-lmbc)+1):
      coords_cleared.append((rmar, rmac + count * lrchange))
      self.map[rmar][rmac+count * lrchange] = 0

    for count in range(1, abs(rmar-lmbr)+1):
      coords_cleared.append((rmar + count * udchange, rmac + (lmbc - rmac)))
      self.map[rmar+count*udchange][rmac+(lmbc-rmac)] = 0

    return coords_cleared

  # returns a path between all points in the list points using A*
  def getPath(self, points):
    num_points = len(points)
    if num_points < 2:
      raise Exception("Path needs at least two points")
    
    # check if any points aren't empty
    for point in points:
      if self.map[point[0]][point[1]] == 1:
        raise Exception("The point (%d, %d) is a wall" % (point[0], point[1]))

    overall_path = []
    for n in range(num_points - 1):
      overall_path.append(points[n])

      # generate path between this point and the next one in the list
      a_star = AStarSearch(self.map)
      intermediate_path = a_star(points[n], points[n+1])
      
      # add to the overall path
      if n > 0:
        intermediate_path.pop(0)
      overall_path.extend(intermediate_path)

    return overall_path

  def _jackalMapFromObstacleMap(self, kernel_size):
    output_size = (self.ob_rows - kernel_size + 1, self.ob_cols - kernel_size + 1)
    jackal_map = [[0 for i in range(output_size[1])] for j in range(output_size[0])]
    
    for r in range(0, self.ob_rows - kernel_size + 1):
      for c in range(0, self.ob_cols - kernel_size + 1):
        if not self._kernelWindowIsOpen(kernel_size, r, c):
          jackal_map[r][c] = 1

    return jackal_map

  def _kernelWindowIsOpen(self, kernel_size, r, c):
    for r_kernel in range(r, r + kernel_size):
      for c_kernel in range(c, c + kernel_size):
        if self.ob_map[r_kernel][c_kernel] == 1:
          return False

    return True

  def _isInMap(self, r, c):
    return r >= 0 and r < self.rows and c >= 0 and c < self.cols

  def getMap(self):
    return self.map

class DifficultyMetrics:
  def __init__(self, map):
    self.map = map
    self.rows = len(map)
    self.cols = len(map[0])

  def density(self, radius):
    dens = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        if self.map[r][c] == 0:
          dens[r][c] = self._densityOfTile(r, c, radius)
        else:
          dens[r][c] = (radius * 2) ** 2

    return dens

  def closestWall(self):
    dists = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        dists[r][c] = self._distToClosestWall(r, c, 0, sys.maxint)

    return dists

  def avgVisibility(self):
    vis = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        vis[r][c] = self._avgVisCell(r, c)

    return vis

  # calculates the number of changes betweeen open & wall
  # in its field of view (along 16 axes)
  def dispersion(self, radius):
    disp = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        disp[r][c] = self._cellDispersion(r, c, radius)

    return disp

  def axis_width(self, axis):
    width = [[0 for i in range(self.cols)] for j in range(self.rows)]
    for r in range(self.rows):
      for c in range(self.cols):
        width[r][c] = self._distance(r, c, axis)

    return width

  def _distance(self, r, c, axis):
    if self.map[r][c] == 1:
      return -1
    
    reverse_axis = (axis[0] * -1, axis[1] * -1)
    dist = 0
    for move in [axis, reverse_axis]:
      r_curr = r
      c_curr = c
      while self.map[r_curr][c_curr] != 1:
        r_curr += move[0]
        c_curr += move[1]

        if r_curr < 0 or r_curr >= self.rows or c_curr < 0 or c_curr >= self.cols:
          break

        if self.map[r_curr][c_curr] != 1:
          dist += 1

    return dist


  def _cellDispersion(self, r, c, radius):
    if self.map[r][c] == 1:
      return -1

    axes_wall = []
    # four cardinal, four diagonal, and one in between each (slope +- 1/2 or 2)
    for move in [(0, 1), (1, 2), (1, 1), (2, 1), (1, 0), (2, -1), (1, -1), (1, -2), (0, -1), (-2, -1), (-1, -1), (-1, -2), (-1, 0), (-2, 1), (-1, 1), (-1, 2)]:
      count = 0
      wall = False
      r_curr = r
      c_curr = c
      while count < radius and not wall:
        r_curr += move[0]
        c_curr += move[1]

        if r_curr < 0 or r_curr >= self.rows or c_curr < 0 or c_curr >= self.cols:
          break

        if self.map[r_curr][c_curr] == 1:
          wall = True

        # count the in-between axes as two steps
        if move[0] == 2 or move[1] == 2:
          count += 2
        else:
          count += 1
      
      if wall:
        axes_wall.append(True)
      else:
        axes_wall.append(False)

    # count the number of changes in this cell's field of view
    change_count = 0
    for i in range(len(axes_wall)-1):
      if axes_wall[i] != axes_wall[i+1]:
        change_count += 1

    if axes_wall[0] != axes_wall[15]:
      change_count += 1

    return change_count


  def _avgVisCell(self, r, c):
    total_vis = 0
    num_axes = 0
    for r_move in [-1, 0, 1]:
      for c_move in [-1, 0, 1]:
        if r_move == 0 and c_move == 0:
          continue

        this_vis = 0
        r_curr = r
        c_curr = c
        wall_found = False
        while not wall_found:
          if r_curr < 0 or r_curr >= self.rows or c_curr < 0 or c_curr >= self.cols:
            break

          if self.map[r_curr][c_curr] == 1:
            wall_found = True
          else:
            this_vis += 1

          r_curr += r_move
          c_curr += c_move
        
        # if ran out of bounds before finding wall, don't count
        if wall_found:
          total_vis += this_vis
          num_axes += 1
    
    return total_vis / num_axes


  def _densityOfTile(self, row, col, radius):
    count = 0
    for r in range(row-radius, row+radius+1):
      for c in range(col-radius, col+radius+1):
        if r >= 0 and r < self.rows and c >= 0 and c < self.cols and (r!=row or c!=col):
          count += self.map[r][c]

    return count   

  # determines how far a given cell is from a wall (non-diagonal)
  def _distToClosestWall(self, r, c, currCount, currBest):
    if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
      return sys.maxint

    if self.map[r][c] == 1:
      return 0

    if currCount >= currBest:
      return sys.maxint

    bestUp = 1 + self._distToClosestWall(r-1, c, currCount+1, currBest)
    if bestUp < currBest:
      currBest = bestUp
    
    bestDown = 1 + self._distToClosestWall(r+1, c, currCount+1, currBest)
    if bestDown < currBest:
      currBest = bestDown
    
    bestLeft = 1 + self._distToClosestWall(r, c-1, currCount+1, currBest)
    if bestLeft < currBest:
      currBest = bestLeft

    bestRight = 1 + self._distToClosestWall(r, c+1, currCount+1, currBest)

    return min(bestUp, bestDown, bestLeft, bestRight)


class AStarSearch:
  def __init__(self, map):
    self.map = map
    self.map_rows = len(map)
    self.map_cols = len(map[0])

  def __call__(self, start_coord, end_coord):
    # initialize start and end nodes
    start_node = Node(None, start_coord)
    start_node.g = start_node.h = start_node.f = 0
    end_node = Node(None, end_coord)
    end_node.g = end_node.h = end_node.f = 0

    # initialize lists to track nodes we've visited or not
    visited = []
    not_visited = []

    # add start to nodes yet to be processed
    not_visited.append(start_node)

    # while there are nodes to process
    while len(not_visited) > 0:
      # get lowest cost next node
      curr_node = not_visited[0]
      curr_idx = 0
      for idx, node in enumerate(not_visited):
        if node.f < curr_node.f:
          curr_node = node
          curr_idx = idx

      # mark this node as processed
      not_visited.pop(curr_idx)
      visited.append(curr_node)

      # if this node is at end of the path, return
      if curr_node == end_node:
        return self.returnPath(curr_node)

      # limit turns to 45 degrees
      valid_moves_dict = {
        (0, 1): [(-1, 1), (0, 1), (1, 1)],
        (1, 1): [(0, 1), (1, 1), (1, 0)],
        (1, 0): [(1, 1), (1, 0), (1, -1)],
        (1, -1): [(1, 0), (1, -1), (0, -1)],
        (0, -1): [(1, -1), (0, -1), (-1, -1)],
        (-1, -1): [(0, -1), (-1, -1), (-1, 0)],
        (-1, 0): [(-1, -1), (-1, 0), (-1, 1)],
        (-1, 1): [(-1, 0), (-1, 1), (0, 1)]
      }

      valid_moves = []
      if curr_node == start_node:
        # if start node, can go any direction
        valid_moves = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
      else:
        # otherwise, can only go straight or 45 degree turn
        moving_direction = (curr_node.r - curr_node.parent.r, curr_node.c - curr_node.parent.c)
        valid_moves = valid_moves_dict.get(moving_direction)

      # find all valid, walkable neighbors of this node
      children = []
      for move in valid_moves:

        # calculate neighbor position
        child_pos = (curr_node.r + move[0], curr_node.c + move[1])
        
        # if outside the map, not possible
        if child_pos[0] < 0 or child_pos[0] >= self.map_rows or child_pos[1] < 0 or child_pos[1] >= self.map_cols:
          continue

        # if a wall tile, not possible
        if self.map[child_pos[0]][child_pos[1]] == 1:
          continue

        # also not possible to move between diagonal walls
        if move[0] != 0 and move[1] != 0 and self.map[curr_node.r+move[0]][curr_node.c] == 1 and self.map[curr_node.r][curr_node.c+move[1]] == 1:
          continue

        # if neighbor is possible to reach, add to list of neighbors
        child_node = Node(curr_node, child_pos)
        children.append(child_node)


      # loop through all walkable neighbors of this node
      for child in children:

        # if neighbor already visited, not usable
        if child in visited:
          continue

        # calculate f, g, h values
        child.g += 1
        child.h = math.sqrt(((child.r - end_node.r) ** 2) + ((child.c - end_node.c) ** 2))
        child.f = child.g + child.h

        # if this node is already in the unprocessed list
        # with a g-value lower than what we have, don't add it
        if len([i for i in not_visited if child == i and child.g > i.g]) > 0:
          continue

        not_visited.append(child)

  # generate the path from start to end
  def returnPath(self, end_node):
    path = []
    curr_node = end_node
    while curr_node != None:
      path.append((curr_node.r, curr_node.c))
      curr_node = curr_node.parent

    path.reverse()
    return path


class Node:
  def __init__(self, parent, coord):
    self.parent = parent
    self.r = coord[0]
    self.c = coord[1]

    self.g = 0
    self.h = 0
    self.f = 0

  def __eq__(self, other):
    return self.r == other.r and self.c == other.c
 

class Display:
  def __init__(self, map, map_with_path, jackal_map, jackal_map_with_path, density_radius, dispersion_radius):
    self.map = map
    self.map_with_path = map_with_path
    self.jackal_map = jackal_map
    self.jackal_map_with_path = jackal_map_with_path
    self.density_radius = density_radius
    self.dispersion_radius = dispersion_radius
  
    diff = DifficultyMetrics(jackal_map)
    self.metrics = {
      "closestDist": diff.closestWall(),
      "density": diff.density(density_radius),
      "avgVis": diff.avgVisibility(),
      "dispersion": diff.dispersion(dispersion_radius),
      "leftright_width": diff.axis_width((0, 1)),
      "updown_width": diff.axis_width((1, 0)),
      "pos_diag_width": diff.axis_width((-1, 1)),
      "neg_diag_width": diff.axis_width((1, 1)),
    }

  def __call__(self):
    fig, ax = plt.subplots(3, 3)
    
    

    # map and path
    map_plot = ax[0][0].imshow(self.map_with_path, cmap='Greys', interpolation='nearest')
    map_plot.axes.get_xaxis().set_visible(False)
    map_plot.axes.get_yaxis().set_visible(False)
    ax[0][0].set_title("Map and A* path")

    # closest wall distance
    dists = self.metrics.get("closestDist")
    dist_plot = ax[0][1].imshow(dists, cmap='RdYlGn', interpolation='nearest')
    dist_plot.axes.get_xaxis().set_visible(False)
    dist_plot.axes.get_yaxis().set_visible(False)
    ax[0][1].set_title("Distance to \nclosest obstacle")
    dist_cbar = fig.colorbar(dist_plot, ax=ax[0][1], orientation='horizontal')
    dist_cbar.ax.tick_params(labelsize='xx-small')

    # density
    densities = self.metrics.get("density")
    density_plot = ax[0][2].imshow(densities, cmap='binary', interpolation='nearest')
    density_plot.axes.get_xaxis().set_visible(False)
    density_plot.axes.get_yaxis().set_visible(False)
    ax[0][2].set_title("%d-square radius density" % self.density_radius)
    dens_cbar = fig.colorbar(density_plot, ax=ax[0][2], orientation='horizontal')
    dens_cbar.ax.tick_params(labelsize='xx-small')

    # average visibility
    avgVis = self.metrics.get("avgVis")
    avgVis_plot = ax[1][0].imshow(avgVis, cmap='RdYlGn', interpolation='nearest')
    avgVis_plot.axes.get_xaxis().set_visible(False)
    avgVis_plot.axes.get_yaxis().set_visible(False)
    ax[1][0].set_title("Average visibility")
    avgVis_cbar = fig.colorbar(avgVis_plot, ax=ax[1][0], orientation='horizontal')
    avgVis_cbar.ax.tick_params(labelsize='xx-small')
    
    # dispersion
    dispersion = self.metrics.get("dispersion")
    disp_plot = ax[1][1].imshow(dispersion, cmap='RdYlGn', interpolation='nearest')
    disp_plot.axes.get_xaxis().set_visible(False)
    disp_plot.axes.get_yaxis().set_visible(False)
    ax[1][1].set_title("%d-square radius dispersion" % self.dispersion_radius)
    disp_cbar = fig.colorbar(disp_plot, ax=ax[1][1], orientation='horizontal')
    disp_cbar.ax.tick_params(labelsize='xx-small')

    # jackal's navigable map, low-res
    jmap_plot = ax[2][0].imshow(self.jackal_map_with_path, cmap='Greys', interpolation='nearest')
    jmap_plot.axes.get_xaxis().set_visible(False)
    jmap_plot.axes.get_yaxis().set_visible(False)
    ax[2][0].set_title("Jackal navigable map")

    plt.delaxes(ax[1][2])
    plt.axis('off')
    plt.show()


class Input:
  def __init__(self):
    self.root = tk.Tk(className="Parameters")

    tk.Label(self.root, text="Seed").grid(row=0)
    tk.Label(self.root, text="Smoothing iterations").grid(row=1)
    tk.Label(self.root, text="Fill percentage (0 to 1)").grid(row=2)
    tk.Label(self.root, text="Rows").grid(row=3, column=0)
    tk.Label(self.root, text="Cols").grid(row=3, column=2)

    self.seed = tk.Entry(self.root)
    self.seed.grid(row=0, column=1)

    self.smoothIter = tk.Entry(self.root)
    self.smoothIter.insert(0, "4")
    self.smoothIter.grid(row=1, column=1)

    self.fillPct = tk.Entry(self.root)
    self.fillPct.insert(0, "0.35")
    self.fillPct.grid(row=2, column=1)

    self.rows = tk.Entry(self.root)
    self.rows.insert(0, "25")
    self.rows.grid(row=3, column=1)

    self.cols = tk.Entry(self.root)
    self.cols.insert(0, "25")
    self.cols.grid(row=3, column=3)

    self.showMetrics = tk.IntVar()
    self.showMetrics.set(True)
    showMetricsBox = tk.Checkbutton(self.root, text="Show metrics", var=self.showMetrics)
    showMetricsBox.grid(row=4, column=1)

    tk.Button(self.root, text='Run', command=self.get_input).grid(row=5, column=1)

    self.root.mainloop()
  
  def get_input(self):
    self.inputs = {}

    # get seed
    if len(self.seed.get()) == 0:
      self.inputs["seed"] = hash(datetime.datetime.now())
    else:
      try:
        self.inputs["seed"] = int(self.seed.get())
      except:
        self.inputs["seed"] = hash(self.seed.get())

    # get number of smoothing iterations
    default_smooth_iter = 4
    try:
      self.inputs["smoothIter"] = int(self.smoothIter.get())
    except:
      self.inputs["smoothIter"] = default_smooth_iter

    # get random fill percentage
    default_fill_pct = 0.35
    try:
      self.inputs["fillPct"] = float(self.fillPct.get())
    except:
      self.inputs["fillPct"] = default_fill_pct

    # get number of rows
    default_rows = 25
    try:
      self.inputs["rows"] = int(self.rows.get())
    except:
      self.inputs["rows"] = default_rows

    # get number of columns
    default_cols = 25
    try:
      self.inputs["cols"] = int(self.cols.get())
    except:
      self.inputs["rows"] = default_cols

    # get show metrics value
    default_show_metrics = 1
    try:
      self.inputs["showMetrics"] = self.showMetrics.get()
    except:
      self.inputs["showMetrics"] = default_show_metrics
      
    self.root.destroy()


def main(iteration=0):

    # dirName = "~/jackal_ws/src/jackal_simulator/jackal_gazebo/worlds/"

    world_file = "world_" + str(iteration) + ".world"
    grid_file = "grid_" + str(iteration) + ".npy"
    path_file = "path_" + str(iteration) + ".npy"

    # get user parameters, if provided
    # inputWindow = Input()
    # inputDict = inputWindow.inputs

    inputDict = { "seed" : hash(datetime.datetime.now()),
                  "smoothIter": 4,
                  "fillPct" : 0.35,
                  "rows" : 25,
                  "cols" : 25,
                  "showMetrics" : 0 }

    # create 25x25 world generator and run smoothing iterations
    print("Seed: %d" % inputDict["seed"])
    obMapGen = ObstacleMap(inputDict["rows"], inputDict["cols"], inputDict["fillPct"], inputDict["seed"], inputDict["smoothIter"])
    obMapGen()

    # get map from the obstacle map generator
    obstacle_map = obMapGen.getMap()
    
    # generate jackal's map from the obstacle map & ensure connectivity
    jMapGen = JackalMap(obstacle_map, def_kernel_size)
    startRegion = jMapGen.biggestLeftRegion()
    endRegion = jMapGen.biggestRightRegion()
    cleared_coords = jMapGen.connectRegions(startRegion, endRegion)

    # get the final jackal map and update the obstacle map
    jackal_map = jMapGen.getMap()
    obstacle_map = obMapGen.updateObstacleMap(cleared_coords, def_kernel_size)

    # write map to .world file
    writer = WorldWriter(world_file, obstacle_map, cyl_radius=0.075)
    writer()

    """ Generate random points to demonstrate path """
    left_open = []
    right_open = []
    for r in range(len(jackal_map)):
      if startRegion[r][0] == 1:
        left_open.append(r)
      if endRegion[r][len(jackal_map[0])-1] == 1:
        right_open.append(r)
    left_coord = left_open[random.randint(0, len(left_open)-1)]
    right_coord = right_open[random.randint(0, len(right_open)-1)]
    """ End random point selection """

    
    # generate path, if possible
    path = []
    print("Points: (%d, 0), (%d, %d)" % (left_coord, right_coord, len(jackal_map[0])-1))
    path = jMapGen.getPath([(left_coord, 0), (right_coord, len(jackal_map[0])-1)])
    print("Found path!")

    # put paths into matrices to display them
    obstacle_map_with_path = [[obstacle_map[j][i] for i in range(len(obstacle_map[0]))] for j in range(len(obstacle_map))]
    jackal_map_with_path = [[jackal_map[j][i] for i in range(len(jackal_map[0]))] for j in range(len(jackal_map))]
    for r, c in path:
      # update jackal-space path display
      jackal_map_with_path[r][c] = 0.35

      # update obstacle-space path display
      for r_kernel in range(r, r + def_kernel_size):
        for c_kernel in range(c, c + def_kernel_size):
          obstacle_map_with_path[r_kernel][c_kernel] = 0.35
    jackal_map_with_path[left_coord][0] = 0.65
    jackal_map_with_path[right_coord][len(jackal_map[0])-1] = 0.65
    obstacle_map_with_path[left_coord][0] = 0.65
    obstacle_map_with_path[right_coord][len(obstacle_map[0])-1] = 0.65

    np_arr = np.asarray(obstacle_map_with_path)
    np.save(grid_file, np_arr)

    
    # display world and heatmap of distances
    if inputDict["showMetrics"]:
      display = Display(obstacle_map, obstacle_map_with_path, jackal_map, jackal_map_with_path, density_radius=3, dispersion_radius=3)
      display()

    # only show the map itself
    else:
      plt.imshow(obstacle_map_with_path, cmap='Greys', interpolation='nearest')
      plt.show()
    

if __name__ == "__main__":
    main()
      for r_kernel in range(r, r + def_kernel_size):
        for c_kernel in range(c, c + def_kernel_size):
          obstacle_map_with_path[r_kernel][c_kernel] = 0.35
    jackal_map_with_path[left_coord][0] = 0.65
    jackal_map_with_path[right_coord][len(jackal_map[0])-1] = 0.65
    obstacle_map_with_path[left_coord][0] = 0.65
    obstacle_map_with_path[right_coord][len(obstacle_map[0])-1] = 0.65

    # display world and heatmap of distances
    if inputDict["showMetrics"]:
      display = Display(obstacle_map, obstacle_map_with_path, jackal_map, jackal_map_with_path, density_radius=3, dispersion_radius=3)
      display()

    # only show the map itself
    else:
      plt.imshow(obstacle_map_with_path, cmap='Greys', interpolation='nearest')
      plt.show()

if __name__ == "__main__":
    main()
