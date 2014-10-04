#!/usr/bin/python

# TODO(mcglincy): figure out why we need this version of python to get 
# the pygame in our pypath

import pygame
import pygame.locals
import pygame.mouse
import pygame.sprite
import pygame.time
import random
import sys
import time


class Game:
  """Global game class."""

  # game constants
  SCREEN_WIDTH = 640
  SCREEN_HEIGHT = 480
  NUM_ANTS = 20

  # game globals
  FOOD = None
  NEST = None
  PHEROMONES = []
  PHEROMONE_MAP = {}


class Nest(pygame.sprite.Sprite):
  """Nest sprite."""
  def __init__(self):
    pygame.sprite.Sprite.__init__(self) 
    self.image, self.rect = LoadImage('nest.jpg', -1)

  def update(self):
    pass


class Picnic(pygame.sprite.Sprite):
  """Picnic sprite."""
  def __init__(self):
    pygame.sprite.Sprite.__init__(self) 
    self.image, self.rect = LoadImage('picnic.jpg', -1)

  def update(self):
    pass


class Pheromone:
  """A pheromone marking, with strength and position."""
  BASE_STRENGTH = 10000
  
  def __init__(self, x, y):
    # TODO: tune strength vs. decay in main pygame loop
    self.strength = Pheromone.BASE_STRENGTH
    self.x = x
    self.y = y    

  @staticmethod
  def AgeAllPheromones():
    """Reduce strength for all existent pheromones, removing strength-less ones."""
    to_be_deleted = []
    for pheromone in Game.PHEROMONES:
      pheromone.strength -= 1
      if pheromone.strength <= 0:
        to_be_deleted.append(pheromone)

    for pheromone in to_be_deleted:
      Game.PHEROMONES.remove(pheromone)
      del Game.PHEROMONE_MAP[(pheromone.x, pheromone.y)]


  @staticmethod
  def MarkNewPheromone(x, y):
    """Mark a new pheromone at x, y position."""
    # update any pre-existing
    pre_existing_pheromone = Game.PHEROMONE_MAP.get((x,y))
    if pre_existing_pheromone:
      pre_existing_pheromone.strength += Pheromone.BASE_STRENGTH
    else:
      # or, add a new one
      new_pheromone = Pheromone(x, y)
      Game.PHEROMONES.append(new_pheromone)
      Game.PHEROMONE_MAP[(x,y)] = new_pheromone

  @staticmethod
  def LookForStrongestPheromone(x, y, area=5):
    """Look for the strongest pheromone around a given position.

    Returns:
      The strongest pheromone, or None if there is no local pheromone.
    """
    strongest_pheromone = None 
    # scan the box around our position
    for x_look in range(x - area, x + area + 1):
      for y_look in range(y - area, y + area + 1):
        found_pheromone = Game.PHEROMONE_MAP.get((x_look, y_look))
        if (found_pheromone and 
            (strongest_pheromone is None or 
             # TODO: temporarily testing weakest
             found_pheromone.strength < strongest_pheromone.strength)):
          strongest_pheromone = found_pheromone
    return strongest_pheromone


class Direction:
  """A compass direction."""
  def __init__(self, name, compass_index, rotate_degrees):
    self.name = name
    self.compass_index = compass_index
    self.rotate_degrees = rotate_degrees

  def TurnLeft(self):
    new_index = self.compass_index - 1
    if new_index < 0:
      new_index = 7
    return COMPASS[new_index]    

  def TurnRight(self):
    new_index = self.compass_index + 1
    if new_index > 7:
      new_index = 0
    return COMPASS[new_index]    

  @staticmethod
  def DirectionToMove(direction):
    """Get an (x, y) move according to our direction."""
    return Direction.DIRECTION_TO_MOVE.get(direction)

  @staticmethod
  def MoveToDirection(move):
    """Get a direction corresponding to an (x, y) move."""
    return Direction.MOVE_TO_DIRECTION.get(move)

  @staticmethod 
  def DirectionFromPositionToPosition(from_x, from_y, to_x, to_y):
    """Get the direction from one position to another."""
    # TODO: do we need to handle from == to?
    # TODO: clarify +/x as per our grid, pygame, thinking :P
    move_x = to_x - from_x
    move_y = to_y - from_y
    if move_x < -1:
      move_x = -1
    elif move_x > 1:
      move_x = 1
    if move_y < -1:
      move_y = -1
    elif move_y > 1:
      move_y = 1
    return Direction.MoveToDirection((move_x, move_y))


# set up direction enum
Direction.NORTH = Direction('north', 0, 0)
Direction.NORTHEAST = Direction('northeast', 1, -45)
Direction.EAST = Direction('east', 2, -90)
Direction.SOUTHEAST = Direction('southeast', 3, -135)
Direction.SOUTH = Direction('south', 4, -180)
Direction.SOUTHWEST = Direction('southwest', 5, -225)
Direction.WEST = Direction('west', 6, -270)
Direction.NORTHWEST = Direction('northwest', 7, -315)
COMPASS = [Direction.NORTH, Direction.NORTHEAST, Direction.EAST, Direction.SOUTHEAST,
           Direction.SOUTH, Direction.SOUTHWEST, Direction.WEST, Direction.NORTHWEST]
Direction.DIRECTION_TO_MOVE = {
    Direction.NORTH: (0, -1),
    Direction.NORTHEAST: (1, -1),
    Direction.EAST: (1, 0),
    Direction.SOUTHEAST: (1, 1),
    Direction.SOUTH: (0, 1),
    Direction.SOUTHWEST: (-1, 1),
    Direction.WEST: (-1, 0),
    Direction.NORTHWEST: (-1, -1),
  }
Direction.MOVE_TO_DIRECTION = {}
for direction, move in Direction.DIRECTION_TO_MOVE.iteritems():
  Direction.MOVE_TO_DIRECTION[move] = direction


class Ant(pygame.sprite.Sprite):
  """The hero of our story."""

  CHANGE_DIRECTION_CHANCE = .04  # per Sprite.update(), so checked a lot...
  MOVE_INCREMENT = 1

  # behaviors
  WANDER = 'wander'
  RETURN_TO_NEST = 'return_to_nest'

  def __init__(self, name='ant'):
    pygame.sprite.Sprite.__init__(self) 
    self.image_master, self.rect = LoadImage('ant.jpg', -1)
    self.image = self.image_master
    self.direction = Direction.NORTH  # sprite image initially pointing this way
    self.behavior = self.WANDER
    self.following_trail = False
    self.name = name

  def update(self):
    """Override Sprite.update()."""
    #self.pos = pygame.mouse.get_pos()
    self.Move()

  def Move(self):
    if self.behavior == self.WANDER:
      self.Wander()
    elif self.behavior == self.RETURN_TO_NEST:
      self.ReturnToNest()

  def Print(self, msg):
    print 'ant [%s (%s, %s) %s] %s' % (
        self.name, self.rect.center[0], self.rect.center[1], self.direction.name, msg)

  def Wander(self):
    # are we at the food?
    if self.rect.colliderect(Game.FOOD.rect):
      #self.Print("FOUND FOOD!")
      self.behavior = self.RETURN_TO_NEST
      self.following_trail = False
      return

    # look for pheromone trail
    pheromone = Pheromone.LookForStrongestPheromone(self.rect.center[0], self.rect.center[1])
    if pheromone:
      pheromone_direction = Direction.DirectionFromPositionToPosition(
          self.rect.center[0], self.rect.center[1], pheromone.x, pheromone.y)
      self.Turn(pheromone_direction)
      if not self.following_trail:
        self.following_trail = True
        #self.Print('found a trail (%s, %s)' % (pheromone.x, pheromone.y))
      else:
        #self.Print('still on the trail (%s, %s)' % (pheromone.x, pheromone.y))
        pass
    else:
      if self.following_trail:
        #self.Print('lost the trail!')
        self.following_trail = False
      if random.random() < self.CHANGE_DIRECTION_CHANCE:
        # random wandering 
        self.Turn()

    # obstacle / boundary avoidance
    if not self.IsMoveAheadClear():
      self.Turn()
    else:
      move = Direction.DirectionToMove(self.direction)
      self.rect.center = (self.rect.center[0] + move[0], self.rect.center[1] + move[1])

  def Turn(self, direction=None):
    """Turn.

    If no direction is supplied, randomly turn left or right.
    """
    if direction:
      self.direction = direction
    else:
      if random.random() < .50:
        self.direction = self.direction.TurnLeft()
      else:
        self.direction = self.direction.TurnRight()
    self.RotateSpriteToDirection()

  def ReturnToNest(self):
    """Time to go home, yo!"""
    if self.rect.colliderect(Game.NEST.rect):
      self.Print('AT NEST!')
      self.behavior = self.WANDER
      return

    # mark pheromone
    Pheromone.MarkNewPheromone(self.rect.center[0], self.rect.center[1])

    move = self.ChooseReturnMove()
    self.Turn(Direction.MoveToDirection(move))
    self.rect.center = (self.rect.center[0] + move[0], self.rect.center[1] + move[1])

  def ChooseReturnMove(self):
    """Choose a move to more-or-less return directly to the nest."""
    x, y = self.rect.center
    nest_x, nest_y = Game.NEST.rect.center
    # need to add randomness / turns
    if x < nest_x:
      delta_x = 1
    elif x > nest_x:
      delta_x = -1
    else:
      delta_x = 0
    if y < nest_y:
      delta_y = 1
    elif y > nest_y:
      delta_y = -1
    else:
      delta_y = 0

    return delta_x, delta_y

  def RotateSpriteToDirection(self):
    self.image = pygame.transform.rotate(self.image_master, self.direction.rotate_degrees)

  def IsMoveAheadClear(self):
    """Check to see if we can move ahead in our current direction."""
    move = Direction.DirectionToMove(self.direction)
    x, y = (self.rect.center[0] + move[0], self.rect.center[1] + move[1])

    # check for screen border
    if x <= 0 or x >= Game.SCREEN_WIDTH or y <= 0 or y >= Game.SCREEN_HEIGHT:
      return False
    
    return True


def LoadImage(name, colorkey=None):
  """Load an image.

  Returns:
    (image, rect)
  """
  try:
    image = pygame.image.load(name)
  except pygame.error, message:
    raise SystemExit, message
  image = image.convert()
  if colorkey is not None:
    if colorkey is -1:
      colorkey = image.get_at((0,0))
    image.set_colorkey(colorkey, pygame.locals.RLEACCEL)
  return image, image.get_rect()

def ProcessInput(events):
  """Handle pygame input."""
  for event in events: 
    if event.type == pygame.locals.QUIT: 
      sys.exit(0) 

def main():
  # initialize pygame
  pygame.init()
  pygame.display.set_mode((640, 480))
  pygame.display.set_caption('Ants!')
  screen = pygame.display.get_surface()
  clock = pygame.time.Clock()
  background = pygame.Surface(screen.get_size())
  background = background.convert()
  background.fill((250, 250, 250))

  Game.NEST = Nest()
  Game.NEST.rect.bottomright = (Game.SCREEN_WIDTH, Game.SCREEN_HEIGHT)
  ants = []
  for i in range(Game.NUM_ANTS):
    ants.append(Ant('#%s' % i))
    ants[i].rect.center = Game.NEST.rect.topleft
  Game.FOOD = Picnic()
  Game.FOOD.rect.topleft = (0, 0)
  all_sprites = pygame.sprite.RenderPlain(tuple(ants) + (Game.NEST, Game.FOOD))

  # main game loop
  while 1:
    clock.tick(60)
    ProcessInput(pygame.event.get())
    all_sprites.update()
    
    Pheromone.AgeAllPheromones()

    # mark pheromones on background
    background.fill((250, 250, 250))
    pxarray = pygame.PixelArray(background)
    for pheromone in Game.PHEROMONES:
        pxarray[pheromone.x][pheromone.y] = (0, 0, 0)
    del pxarray

    screen.blit(background, (0, 0))
    all_sprites.draw(screen)
    pygame.display.flip()

if __name__ == '__main__':
  main()
