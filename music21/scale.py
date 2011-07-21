# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         scale.py
# Purpose:      music21 classes for representing scales
#
# Authors:      Michael Scott Cuthbert
#               Christopher Ariza
#               Jose Cabal-Ugaz
#
# Copyright:    (c) 2009-2011 The music21 Project
# License:      LGPL
#-------------------------------------------------------------------------------

'''
The various Scale objects provide a bi-directional object representation 
of octave repeating and non-octave repeating scales built by network of 
:class:`~music21.interval.Interval` objects as modeled in 
:class:`~music21.intervalNetwork.BoundIntervalNetwork`.


The main public interface to these resources are subclasses of
:class:`~music21.scale.ConcreteScale`, such as 
:class:`~music21.scale.MajorScale`, :class:`~music21.scale.MinorScale`, 
and :class:`~music21.scale.MelodicMinorScale`.


More unusual scales are also available, such as 
:class:`~music21.scale.OctatonicScale`, 
:class:`~music21.scale.SieveScale`, and :class:`~music21.scale.RagMarwa`.


All :class:`~music21.scale.ConcreteScale` subclasses provide the ability 
to get a pitches across any range, get a pitch for scale step, get a 
scale step for pitch, and, for any given pitch ascend or descend to the 
next pitch. In all cases :class:`~music21.pitch.Pitch` objects are returned.


>>> from music21 import *
>>> sc1 = scale.MajorScale('a')
>>> sc1.getPitches('g2', 'g4')
[G#2, A2, B2, C#3, D3, E3, F#3, G#3, A3, B3, C#4, D4, E4, F#4]


>>> sc2 = scale.MelodicMinorScale('a')
>>> sc2.getPitches('g2', 'g4', direction='descending')
[G4, F4, E4, D4, C4, B3, A3, G3, F3, E3, D3, C3, B2, A2, G2]
>>> sc2.getPitches('g2', 'g4', direction='ascending')
[G#2, A2, B2, C3, D3, E3, F#3, G#3, A3, B3, C4, D4, E4, F#4]


>>> # a sieve-based scale using Xenakis's representation of the Major scale
>>> sc3 = scale.SieveScale('a', '(-3@2 & 4) | (-3@1 & 4@1) | (3@2 & 4@2) | (-3 & 4@3)')
>>> sc3.getPitches('g2', 'g4')
[G#2, A2, B2, C#3, D3, E3, F#3, G#3, A3, B3, C#4, D4, E4, F#4]
    


'''

import copy
import unittest, doctest
import re

import music21
from music21 import common
from music21 import pitch
from music21 import interval
from music21 import intervalNetwork
from music21 import sieve
from music21 import scala

from music21.musicxml import translate as musicxmlTranslate

from music21 import environment
_MOD = "scale.py"
environLocal = environment.Environment(_MOD)

DIRECTION_BI = intervalNetwork.DIRECTION_BI
DIRECTION_ASCENDING = intervalNetwork.DIRECTION_ASCENDING
DIRECTION_DESCENDING = intervalNetwork.DIRECTION_DESCENDING

TERMINUS_LOW = intervalNetwork.TERMINUS_LOW
TERMINUS_HIGH = intervalNetwork.TERMINUS_HIGH

#-------------------------------------------------------------------------------
class ScaleException(Exception):
    pass

class Scale(music21.Music21Object):
    '''
    Generic base class for all scales, both abstract and concrete.
    '''
    def __init__(self):
        self.type = 'Scale' # could be mode, could be other indicator


    def _getName(self):
        '''Return or construct the name of this scale
        '''
        return self.type
        
    name = property(_getName, 
        doc = '''Return or construct the name of this scale.

        ''')

    def _isConcrete(self):
        return False

    isConcrete = property(_isConcrete, 
        doc = '''To be concrete, a Scale must have a defined tonic. 
        An abstract Scale is not Concrete, nor is a Concrete scale 
        without a defined tonic.
        ''')

    def _extractPitchList(self, other, comparisonAttribute='nameWithOctave'):
        '''Given a data format, extract all unique pitch space or pitch class values.
        '''
        pre = []
        # if a ConcreteScale, Chord or Stream
        if hasattr(other, 'pitches'):
            pre = other.pitches
        # if a list
        elif common.isListLike(other):
            # assume a list of pitches; possible permit conversions?
            pre = other
        elif hasattr(other, 'pitch'):
            pre = [other.pitch] # get pitch attribute
        return pre




# instead of classes, these can be attributes on the scale object
# class DirectionlessScale(Scale):
#     '''A DirectionlessScale is the same ascending and descending.
#     For instance, the major scale.  
# 
#     A DirectionSensitiveScale has
#     two different forms.  For instance, the natural-minor scale.
#     
#     One could imagine more complex scales that have different forms
#     depending on what scale degree you've just landed on.  Some
#     Ragas might be expressible in that way.'''
#     
#     def ascending(self):
#         return self.pitches
#     
#     def descending(self):
#         tempScale = copy(self.pitches)
#         return tempScale.reverse()
#         ## we perform the reverse on a copy of the pitchList so that
#         ## in case we are multithreaded later in life, we do not have
#         ## a race condition where someone might get self.pitches as
#         ## reversed
# 
# class DirectionSensitiveScale(Scale):
#     pass


#-------------------------------------------------------------------------------
class AbstractScale(Scale):
    '''
    An abstract scale is specific scale formation, but does not have a 
    defined pitch collection or pitch reference. For example, all Major 
    scales can be represented by an AbstractScale; a ConcreteScale, 
    however, is a specific Major Scale, such as G Major. 

    These classes provide an interface to, and create and manipulate, 
    the stored :class:`~music21.intervalNetwork.BoundIntervalNetwork` 
    object. Thus, they are rarely created or manipulated directly by 
    most users.

    The AbstractScale additionally stores an `_alteredDegrees` dictionary. 
    Subclasses can define altered nodes in AbstractScale that are passed 
    to the :class:`~music21.intervalNetwork.BoundIntervalNetwork`.

    '''
    def __init__(self):
        Scale.__init__(self)
        # store interval network within abstract scale
        self._net = None
        # in most cases tonic/final of scale is step one, but not always
        self.tonicDegree = 1 # step of tonic

        # declare if this scale is octave duplicating
        # can be used as to optimize pitch gathering
        self.octaveDuplicating = True

        # passed to intervalnetwork
        self.deterministic = True
        # store parameter for interval network-based node modifcations
        # entries are in the form: 
        # step: {'direction':DIRECTION_BI, 'interval':Interval}
        self._alteredDegrees = {}

    def __eq__(self, other):
        '''
        >>> from music21 import *
        >>> as1 = scale.AbstractScale()
        >>> as2 = scale.AbstractScale()
        >>> as1 == as2
        True
        >>> as1 == None
        False
        >>> as1.isConcrete
        False
        '''
        # have to test each so as not to confuse with a subclass
        if (isinstance(other, self.__class__) and 
            isinstance(self, other.__class__) and 
            self.tonicDegree == other.tonicDegree and
            self._net == other._net
            ):
            return True     
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)


    def _buildNetwork(self):
        '''Calling the _buildNetwork, with or without parameters, is main job of the AbstractScale class.
        '''
        pass

    def buildNetworkFromPitches(self, pitchList):
        '''
        Builds the network (list of motions) for an abstract scale from a list of pitch.Pitch objects.  If
        the concluding note (usually the "octave") is not given, then it'll be created automatically.
        
        
        Here we treat the augmented triad as a scale:
        
        
        >>> from music21 import *
        >>> p1 = pitch.Pitch("C4")
        >>> p2 = pitch.Pitch("E4")
        >>> p3 = pitch.Pitch("G#4")
        >>> absc = scale.AbstractScale()
        >>> absc.buildNetworkFromPitches([p1, p2, p3])
        >>> absc.octaveDuplicating
        True
        >>> absc._net
        <music21.intervalNetwork.BoundIntervalNetwork object at 0x...>
        
        
        Now see it return a new "scale" of the augmentedTriad on D5
        
        
        >>> absc._net.realizePitch('D5')
        [D5, F#5, A#5, D6]
        
        '''
        pitchListReal = []
        for p in pitchList:
            if common.isStr(p):
                pitchListReal.append(pitch.Pitch(p))
            elif hasattr(p, 'classes') and 'GeneralNote' in p.classes:
                pitchListReal.append(p.pitch)
            else: # assume this is a pitch object
                pitchListReal.append(p)
        pitchList = pitchListReal

        if not common.isListLike(pitchList) or len(pitchList) < 1:
            raise ScaleException("Cannot build a network from this pitch list: %s" % pitchList)
        intervalList = []
        for i in range(len(pitchList) - 1):
            intervalList.append(interval.notesToInterval(pitchList[i], pitchList[i+1]))
        if pitchList[-1].name == pitchList[0].name: # the completion of the scale has been given.
            #print ("hi %s " % pitchList)
            # this scale is only octave duplicating if the top note is exactly
            # 1 octave above the bottom; if it spans more thane one active, 
            # all notes must be identical in each octave
            #if abs(pitchList[-1].ps - pitchList[0].ps) == 12:
            span = interval.notesToInterval(pitchList[0], pitchList[-1])
            #environLocal.printDebug(['got span', span, span.name])
            if span.name  == 'P8':
                self.octaveDuplicating = True
            else:
                self.octaveDuplicating = False
        else:
            p = copy.deepcopy(pitchList[0])
            if pitchList[-1] > pitchList[0]: # ascending
                while p.ps < pitchList[-1].ps:
                    p.octave += 1
            else:
                while p.ps < pitchList[-1].ps:
                    p.octave += -1
            
            intervalList.append(interval.notesToInterval(pitchList[-1], p))
            span = interval.notesToInterval(pitchList[0], p)
            #environLocal.printDebug(['got span', span, span.name])
            if span.name  == 'P8':
                self.octaveDuplicating = True
            else:
                self.octaveDuplicating = False

#             if abs(p.ps - pitchList[0].ps) == 12:
#                 self.octaveDuplicating == True
#             else:
#                 self.octaveDuplicating == False
        
        #environLocal.printDebug(['intervalList', intervalList, 'self.octaveDuplicating', self.octaveDuplicating])
        self._net = intervalNetwork.BoundIntervalNetwork(intervalList,
                    octaveDuplicating=self.octaveDuplicating)



    def getDegreeMaxUnique(self):
        '''Return the maximum number of scale steps, or the number to use as a 
        modulus. 
        '''
        # access from property
        return self._net.degreeMaxUnique

#     def reverse(self):
#         '''Reverse all intervals in this scale.
#         '''
#         pass

    # expose interface from network. these methods must be called (and not
    # ._net directly because they can pass the alteredDegrees dictionary

    def getRealization(self, pitchObj, stepOfPitch,      
         minPitch=None, maxPitch=None, direction=DIRECTION_ASCENDING, reverse=False):
        '''
        Realize the abstract scale as a list of pitch objects, 
        given a pitch object, the step of that pitch object, 
        and a min and max pitch.
        '''
        if self._net is None:
            raise ScaleException('no BoundIntervalNetwork is defined by this "scale".')

        post = self._net.realizePitch(pitchObj, stepOfPitch, 
            minPitch=minPitch, maxPitch=maxPitch,
            alteredDegrees=self._alteredDegrees, direction=direction,
            reverse=reverse)
        # here, we copy the list of pitches so as not to allow editing of 
        # cached pitch values later
        return copy.deepcopy(post)


    def getIntervals(self, stepOfPitch=None,      
         minPitch=None, maxPitch=None, direction=DIRECTION_ASCENDING, reverse=False):
        '''
        Realize the abstract scale as a list of pitch 
        objects, given a pitch object, the step of 
        that pitch object, and a min and max pitch.
        '''
        if self._net is None:
            raise ScaleException('no network is defined.')

        post = self._net.realizeIntervals(stepOfPitch, 
            minPitch=minPitch, maxPitch=maxPitch,
            alteredDegrees=self._alteredDegrees, direction=direction,
            reverse=reverse)
        # here, we copy the list of pitches so as not to allow editing of 
        # cached pitch values later
        return post


    def getPitchFromNodeDegree(self, pitchReference, nodeName, nodeDegreeTarget, 
            direction=DIRECTION_ASCENDING, minPitch=None, maxPitch=None,
            equateTermini=True):
        '''Get a pitch for desired scale degree.
        '''
        post = self._net.getPitchFromNodeDegree(
            pitchReference=pitchReference, # pitch defined here
            nodeName=nodeName, # defined in abstract class
            nodeDegreeTarget=nodeDegreeTarget, # target looking for
            direction=direction, 
            minPitch=minPitch, 
            maxPitch=maxPitch,
            alteredDegrees=self._alteredDegrees,
            equateTermini=equateTermini
            )
        return copy.deepcopy(post)



    def realizePitchByDegree(self, pitchReference, nodeId, nodeDegreeTargets, 
        direction=DIRECTION_ASCENDING, minPitch=None, maxPitch=None):        
        '''Given one or more scale degrees, return a list of all matches over the entire range. 
        '''
        # TODO: rely here on intervalNetwork for caching
        post = self._net.realizePitchByDegree(
            pitchReference=pitchReference, # pitch defined here
            nodeId=nodeId, # defined in abstract class
            nodeDegreeTargets=nodeDegreeTargets, # target looking for
            direction=direction, 
            minPitch=minPitch, 
            maxPitch=maxPitch,
            alteredDegrees=self._alteredDegrees
            )
        return copy.deepcopy(post)


    def getRelativeNodeDegree(self, pitchReference, nodeName, pitchTarget, 
            comparisonAttribute='pitchClass', direction=DIRECTION_ASCENDING):
        '''Expose functionality from :class:`~music21.intervalNetwork.BoundIntervalNetwork`, passing on the stored alteredDegrees dictionary.
        '''
        post = self._net.getRelativeNodeDegree(
            pitchReference=pitchReference, 
            nodeName=nodeName, 
            pitchTarget=pitchTarget,      
            comparisonAttribute=comparisonAttribute,
            direction=direction,
            alteredDegrees=self._alteredDegrees
            )
        return copy.deepcopy(post)


    def nextPitch(self, pitchReference, nodeName, pitchOrigin,
             direction=DIRECTION_ASCENDING, stepSize=1, getNeighbor=True):
        '''
        Expose functionality from :class:`~music21.intervalNetwork.BoundIntervalNetwork`, 
        passing on the stored alteredDegrees dictionary.
        '''
        post = self._net.nextPitch(
            pitchReference=pitchReference, 
            nodeName=nodeName, 
            pitchOrigin=pitchOrigin,      
            direction=direction,
            stepSize = stepSize,
            alteredDegrees=self._alteredDegrees,
            getNeighbor = getNeighbor
            )
        return copy.deepcopy(post)


    def getNewTonicPitch(self, pitchReference, nodeName, 
        direction=DIRECTION_ASCENDING, minPitch=None, maxPitch=None):
        '''
        Define a pitch target and a node. 
        '''
        post = self._net.getPitchFromNodeDegree(
            pitchReference=pitchReference, 
            nodeName=nodeName, 
            nodeDegreeTarget=1, # get the pitch of the tonic 
            direction=direction, 
            minPitch=minPitch, 
            maxPitch=maxPitch,
            alteredDegrees=self._alteredDegrees
            )
        return copy.deepcopy(post)


    #---------------------------------------------------------------------------
    def getScalaStorage(self, direction=DIRECTION_ASCENDING):
        '''Get interval sequence
        '''
        # get one octave of intervals
        ss = scala.ScalaStorage()
        ss.setIntervalSequence(self.getIntervals(direction=direction))
        ss.description = self.__repr__()
        return ss

    def write(self, fmt=None, fp=None, direction=DIRECTION_ASCENDING):
        '''Write the scale in a format. Here, prepare scala format if requested.
        '''
        if fmt is not None:
            format, ext = common.findFormat(fmt)
            if fp is None:
                fpLocal = environLocal.getTempFile(ext)
            if format in ['scala']:
                ss = self.getScalaStorage(direction=direction)
                sf = scala.ScalaFile(ss) # pass storage to the file
                sf.open(fpLocal, 'w')
                sf.write()
                sf.close()
                return fpLocal
        return Scale.write(self, fmt=fmt, fp=fp)


    def show(self, fmt=None, app=None, direction=DIRECTION_ASCENDING):
        '''Show the scale in a format. Here, prepare scala format if requested.
        '''
        if fmt is not None:
            format, ext = common.findFormat(fmt)
            if format in ['scala']:
                returnedFilePath = self.write(format, direction=direction)
                environLocal.launch(format, returnedFilePath, app=app)
                return
        Scale.show(self, fmt=fmt, app=app)


    def _getNetworkxGraph(self):
        '''Create a networx graph from the stored network.
        '''
        return self._net._getNetworkxGraph()

    networkxGraph = property(_getNetworkxGraph, doc='''
        Return a networks Graph object representing a realized version of this :class:`~music21.intervalNetwork.BoundIntervalNetwork`.
        ''')



    def plot(self, *args, **keywords):
        '''Create and display a plot.
        '''
#         >>> from music21 import *
#         >>> s = corpus.parse('bach/bwv324.xml') #_DOCS_HIDE
#         >>> s.plot('pianoroll', doneAction=None) #_DOCS_HIDE
#         >>> #_DOCS_SHOW s = corpus.parse('bach/bwv57.8')
#         >>> #_DOCS_SHOW s.plot('pianoroll')
    
#         .. image:: images/PlotHorizontalBarPitchSpaceOffset.*
#             :width: 600

        # import is here to avoid import of matplotlib problems
        from music21 import graph
        # first ordered arg can be method type
        g = graph.GraphNetworxGraph( 
            networkxGraph=self._getNetworkxGraph(), *args, **keywords)
            # for pitched version
            #networkxGraph=self._getNetworkxRealizedGraph(pitchObj=pitchObj, nodeId=nodeId, minPitch=minPitch, maxPitch=maxPitch))
        g.process()




#-------------------------------------------------------------------------------
# abstract subclasses


class AbstractDiatonicScale(AbstractScale):

    def __init__(self, mode=None):
        AbstractScale.__init__(self)
        self.type = 'Abstract Diatonic'
        self.tonicDegree = None # step of tonic
        self.dominantDegree = None # step of dominant
        # all diatonic scales are octave duplicating
        self.octaveDuplicating = True
        self._buildNetwork(mode=mode)

    def __eq__(self, other):
        '''
        >>> from music21 import *
        >>> as1 = scale.AbstractDiatonicScale('major')
        >>> as2 = scale.AbstractDiatonicScale('lydian')
        >>> as3 = scale.AbstractDiatonicScale('ionian')
        >>> as1 == as2
        False
        >>> as1 == as3
        True
        '''
        # have to test each so as not to confuse with a subclass
        if (isinstance(other, self.__class__) and 
            isinstance(self, other.__class__) and 
            self.type == other.type and
            self.tonicDegree == other.tonicDegree and
            self.dominantDegree == other.dominantDegree and
            self._net == other._net
            ):
            return True     
        else:
            return False

    def _buildNetwork(self, mode=None):
        '''Given sub-class dependent parameters, build and assign the BoundIntervalNetwork.

        >>> from music21 import *
        >>> sc = scale.AbstractDiatonicScale()
        >>> sc._buildNetwork('lydian')
        >>> sc.getRealization('f4', 1, 'f2', 'f6') 
        [F2, G2, A2, B2, C3, D3, E3, F3, G3, A3, B3, C4, D4, E4, F4, G4, A4, B4, C5, D5, E5, F5, G5, A5, B5, C6, D6, E6, F6]
        '''
        # reference: http://cnx.org/content/m11633/latest/
        # most diatonic scales will start with this collection
        srcList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        if mode in ['dorian']:
            intervalList = srcList[1:] + srcList[:1] # d to d
            self.tonicDegree = 1
            self.dominantDegree = 5
            self.relativeMajorDegree = 7
            self.relativeMinorDegree = 5
        elif mode in ['phrygian']:
            intervalList = srcList[2:] + srcList[:2] # e to e
            self.tonicDegree = 1
            self.dominantDegree = 5
            self.relativeMajorDegree = 6
            self.relativeMinorDegree = 4
        elif mode in ['lydian']:
            intervalList = srcList[3:] + srcList[:3] # f to f
            self.tonicDegree = 1
            self.dominantDegree = 5
            self.relativeMajorDegree = 5
            self.relativeMinorDegree = 3
        elif mode in ['mixolydian']:
            intervalList = srcList[4:] + srcList[:4] # g to g
            self.tonicDegree = 1
            self.dominantDegree = 5
            self.relativeMajorDegree = 4
            self.relativeMinorDegree = 2
        elif mode in ['hypodorian']:
            intervalList = srcList[5:] + srcList[:5] # a to a
            self.tonicDegree = 4
            self.dominantDegree = 6
            self.relativeMajorDegree = 3
            self.relativeMinorDegree = 1
        elif mode in ['hypophrygian']:
            intervalList = srcList[6:] + srcList[:6] # b to b
            self.tonicDegree = 4
            self.dominantDegree = 7
            self.relativeMajorDegree = 2
            self.relativeMinorDegree = 7
        elif mode in ['hypolydian']: # c to c
            intervalList = srcList
            self.tonicDegree = 4
            self.dominantDegree = 6
            self.relativeMajorDegree = 1
            self.relativeMinorDegree = 6
        elif mode in ['hypomixolydian']:
            intervalList = srcList[1:] + srcList[:1] # d to d
            self.tonicDegree = 4
            self.dominantDegree = 7
            self.relativeMajorDegree = 7
            self.relativeMinorDegree = 5
        elif mode in ['aeolian', 'minor']:
            intervalList = srcList[5:] + srcList[:5] # a to A
            self.tonicDegree = 1
            self.dominantDegree = 5
            self.relativeMajorDegree = 3
            self.relativeMinorDegree = 1
        elif mode in [None, 'major', 'ionian']: # c to C
            intervalList = srcList
            self.tonicDegree = 1
            self.dominantDegree = 5
            self.relativeMajorDegree = 1
            self.relativeMinorDegree = 6
        elif mode in ['locrian']:
            intervalList = srcList[6:] + srcList[:6] # b to B
            self.tonicDegree = 1
            self.dominantDegree = 5
            self.relativeMajorDegree = 2
            self.relativeMinorDegree = 7
        elif mode in ['hypoaeolian']:
            intervalList = srcList[2:] + srcList[:2] # e to e
            self.tonicDegree = 4
            self.dominantDegree = 6
            self.relativeMajorDegree = 6
            self.relativeMinorDegree = 4
        elif mode in ['hupomixolydian']:
            intervalList = srcList[3:] + srcList[:3] 
            self.tonicDegree = 4
            self.dominantDegree = 7
            self.relativeMajorDegree = 5
            self.relativeMinorDegree = 3
        elif mode in ['hypolocrian']:
            intervalList = srcList[3:] + srcList[:3] # f to f
            self.tonicDegree = 4
            self.dominantDegree = 6
            self.relativeMajorDegree = 5
            self.relativeMinorDegree = 3
        else:
            raise ScaleException('cannot create a scale of the following mode:' % mode)
        self._net = intervalNetwork.BoundIntervalNetwork(intervalList, 
                    octaveDuplicating=self.octaveDuplicating)


class AbstractOctatonicScale(AbstractScale):
    '''Abstract scale representing the two octatonic scales.
    '''
    def __init__(self, mode=None):
        AbstractScale.__init__(self)
        self.type = 'Abstract Octatonic'
        # all octatonic scales are octave duplicating
        self.octaveDuplicating = True
        # here, accept None
        self._buildNetwork(mode=mode)

    def _buildNetwork(self, mode=None):
        '''
        Given sub-class dependent parameters, build and assign the BoundIntervalNetwork.

        >>> from music21 import *
        >>> sc = scale.AbstractDiatonicScale()
        >>> sc._buildNetwork('lydian')
        >>> sc.getRealization('f4', 1, 'f2', 'f6') 
        [F2, G2, A2, B2, C3, D3, E3, F3, G3, A3, B3, C4, D4, E4, F4, G4, A4, B4, C5, D5, E5, F5, G5, A5, B5, C6, D6, E6, F6]

        '''
        srcList = ['M2', 'm2', 'M2', 'm2', 'M2', 'm2', 'M2', 'm2']
        if mode in [None, 2, 'M2']:
            intervalList = srcList # start with M2
            self.tonicDegree = 1
        elif mode in [1, 'm2']:
            intervalList = srcList[1:] + srcList[:1] # start with m2
            self.tonicDegree = 1
        else:
            raise ScaleException('cannot create a scale of the following mode:' % mode)
        self._net = intervalNetwork.BoundIntervalNetwork(intervalList,
                                octaveDuplicating=self.octaveDuplicating)
        # might also set weights for tonic and dominant here



class AbstractHarmonicMinorScale(AbstractScale):
    '''A true bi-directional scale that with the augmented second to a leading tone. 
    '''
    def __init__(self, mode=None):
        AbstractScale.__init__(self)
        self.type = 'Abstract Harmonic Minor'
        self.octaveDuplicating = True
        self._buildNetwork()


    def _buildNetwork(self):
        '''
        '''
        srcList = ['M2', 'M2', 'm2', 'M2', 'M2', 'M2', 'm2']
        intervalList = srcList[5:] + srcList[:5] # a to A
        self.tonicDegree = 1
        self.dominantDegree = 5
        self._net = intervalNetwork.BoundIntervalNetwork(intervalList, 
                        octaveDuplicating=self.octaveDuplicating)

        # raise the seventh in all directions
        # 7 here is scale step/degree, not node id
        self._alteredDegrees[7] = {'direction': intervalNetwork.DIRECTION_BI, 
                               'interval': interval.Interval('a1')}


class AbstractMelodicMinorScale(AbstractScale):
    '''A directional scale. 
    '''
    def __init__(self, mode=None):
        AbstractScale.__init__(self)
        self.type = 'Abstract Melodic Minor'
        self.octaveDuplicating = True
        self._buildNetwork()

    def _buildNetwork(self):
        self.tonicDegree = 1
        self.dominantDegree = 5
# this is now stored in interval network, as it is useful for testing
#         nodes = ({'id':'terminusLow', 'degree':1}, # a
#                  {'id':0, 'degree':2}, # b
#                  {'id':1, 'degree':3}, # c
#                  {'id':2, 'degree':4}, # d
#                  {'id':3, 'degree':5}, # e
# 
#                  {'id':4, 'degree':6}, # f# ascending
#                  {'id':5, 'degree':6}, # f
#                  {'id':6, 'degree':7}, # g# ascending
#                  {'id':7, 'degree':7}, # g
#                  {'id':'terminusHigh', 'degree':8}, # a
#                 )
# 
#         edges = ({'interval':'M2', 'connections':(
#                         [TERMINUS_LOW, 0, DIRECTION_BI], # a to b
#                     )},
#                 {'interval':'m2', 'connections':(
#                         [0, 1, DIRECTION_BI], # b to c
#                     )},
#                 {'interval':'M2', 'connections':(
#                         [1, 2, DIRECTION_BI], # c to d
#                     )},
#                 {'interval':'M2', 'connections':(
#                         [2, 3, DIRECTION_BI], # d to e
#                     )},
# 
#                 {'interval':'M2', 'connections':(
#                         [3, 4, DIRECTION_ASCENDING], # e to f#
#                     )},
#                 {'interval':'M2', 'connections':(
#                         [4, 6, DIRECTION_ASCENDING], # f# to g#
#                     )},
#                 {'interval':'m2', 'connections':(
#                         [6, TERMINUS_HIGH, DIRECTION_ASCENDING], # g# to a
#                     )},
# 
#                 {'interval':'M2', 'connections':(
#                         [TERMINUS_HIGH, 7, DIRECTION_DESCENDING], # a to g
#                     )},
#                 {'interval':'M2', 'connections':(
#                         [7, 5, DIRECTION_DESCENDING], # g to f
#                     )},
#                 {'interval':'m2', 'connections':(
#                         [5, 3, DIRECTION_DESCENDING], # f to e
#                     )},
#                 )

        self._net = intervalNetwork.BoundIntervalNetwork(
                        octaveDuplicating=self.octaveDuplicating)
        # using representation stored in interval network
        #self._net.fillArbitrary(nodes, edges)
        self._net.fillMelodicMinor()


class AbstractCyclicalScale(AbstractScale):
    '''A scale of any size built with an interval list of any form. The resulting scale may be non octave repeating.
    '''
    def __init__(self, mode=None):
        AbstractScale.__init__(self)
        self.type = 'Abstract Cyclical'
        self.octaveDuplicating = False
        self._buildNetwork(mode=mode)

        # cannot assume that abstract cyclical scales are octave duplicating
        # until we have the intervals in use

    def _buildNetwork(self, mode):
        '''
        Here, mode is the list of intervals. 
        '''
        if not common.isListLike(mode):
            mode = [mode] # place in list

        self.tonicDegree = 1
        self._net = intervalNetwork.BoundIntervalNetwork(mode, 
                        octaveDuplicating=self.octaveDuplicating)





class AbstractOctaveRepeatingScale(AbstractScale):
    '''
    A scale of any size built with an interval list 
    that assumes octave completion. An additional 
    interval to complete the octave will be added 
    to the provided intervals. This does not guarantee 
    that the octave will be repeated in one octave, 
    only the next octave above the last interval will 
    be provided. 
    '''
    def __init__(self, mode=None):
        AbstractScale.__init__(self)
        self.type = 'Abstract Octave Repeating'

        if mode is None:
            # supply a default
            mode = ['P8']
        self._buildNetwork(mode=mode)

        # by definition, these are forced to be octave duplicating
        # though, do to some intervals, duplication may not happen every oct
        self.octaveDuplicating = True


    def _buildNetwork(self, mode):
        '''
        Here, mode is the list of intervals. 
        '''
        if not common.isListLike(mode):
            mode = [mode] # place in list
        # get the interval to complete the octave

        intervalSum = interval.add(mode)
        iComplement = intervalSum.complement
        if iComplement is not None:
            mode.append(iComplement)

        self.tonicDegree = 1
        self._net = intervalNetwork.BoundIntervalNetwork(mode, 
                        octaveDuplicating=self.octaveDuplicating)








class AbstractRagAsawari(AbstractScale):
    '''A pseudo raga-scale. 
    '''
    def __init__(self):
        AbstractScale.__init__(self)
        self.type = 'Abstract Rag Asawari'
        self.octaveDuplicating = True
        self._buildNetwork()

    def _buildNetwork(self):
        self.tonicDegree = 1
        self.dominantDegree = 5
        nodes = ({'id':'terminusLow', 'degree':1}, # c
                 {'id':0, 'degree':2}, # d
                 {'id':1, 'degree':4}, # f
                 {'id':2, 'degree':5}, # g
                 {'id':3, 'degree':6}, # a-
                 {'id':'terminusHigh', 'degree':8}, # c

                 {'id':4, 'degree':7}, # b-
                 {'id':5, 'degree':6}, # a-
                 {'id':6, 'degree':5}, # g
                 {'id':7, 'degree':4}, # f
                 {'id':8, 'degree':3}, # e-
                 {'id':9, 'degree':2}, # d
                )
        edges = (
                # ascending
                {'interval':'M2', 'connections':(
                        [TERMINUS_LOW, 0, DIRECTION_ASCENDING], # c to d
                    )},
                {'interval':'m3', 'connections':(
                        [0, 1, DIRECTION_ASCENDING], # d to f
                    )},
                {'interval':'M2', 'connections':(
                        [1, 2, DIRECTION_ASCENDING], # f to g
                    )},
                {'interval':'m2', 'connections':(
                        [2, 3, DIRECTION_ASCENDING], # g to a-
                    )},
                {'interval':'M3', 'connections':(
                        [3, TERMINUS_HIGH, DIRECTION_ASCENDING], # a- to c
                    )},
                # descending
                {'interval':'M2', 'connections':(
                        [TERMINUS_HIGH, 4, DIRECTION_DESCENDING], # c to b-
                    )},
                {'interval':'M2', 'connections':(
                        [4, 5, DIRECTION_DESCENDING], # b- to a-
                    )},
                {'interval':'m2', 'connections':(
                        [5, 6, DIRECTION_DESCENDING], # a- to g
                    )},
                {'interval':'M2', 'connections':(
                        [6, 7, DIRECTION_DESCENDING], # g to f
                    )},
                {'interval':'M2', 'connections':(
                        [7, 8, DIRECTION_DESCENDING], # f to e-
                    )},
                {'interval':'m2', 'connections':(
                        [8, 9, DIRECTION_DESCENDING], # e- to d
                    )},
                {'interval':'M2', 'connections':(
                        [9, TERMINUS_LOW, DIRECTION_DESCENDING], # d to c
                    )},
                )

        self._net = intervalNetwork.BoundIntervalNetwork(
                        octaveDuplicating=self.octaveDuplicating)
        # using representation stored in interval network
        self._net.fillArbitrary(nodes, edges)




class AbstractRagMarwa(AbstractScale):
    '''A pseudo raga-scale. 
    '''
    def __init__(self):
        AbstractScale.__init__(self)
        self.type = 'Abstract Rag Marwa'
        self.octaveDuplicating = True 
        self._buildNetwork()

    def _buildNetwork(self):
        self.tonicDegree = 1
        self.dominantDegree = 5
        nodes = ({'id':'terminusLow', 'degree':1}, # c
                 {'id':0, 'degree':2}, # d-
                 {'id':1, 'degree':3}, # e
                 {'id':2, 'degree':4}, # f#
                 {'id':3, 'degree':5}, # a
                 {'id':4, 'degree':6}, # b
                 {'id':5, 'degree':7}, # a (could use id 3 again?)
                 {'id':'terminusHigh', 'degree':8}, # c

                 {'id':6, 'degree':7}, # d- (above terminus)
                 {'id':7, 'degree':6}, # b
                 {'id':8, 'degree':5}, # a
                 {'id':9, 'degree':4}, # f#
                 {'id':10, 'degree':3}, # e
                 {'id':11, 'degree':2}, # d-
                )
        edges = (
                # ascending
                {'interval':'m2', 'connections':(
                        [TERMINUS_LOW, 0, DIRECTION_ASCENDING], # c to d-
                    )},
                {'interval':'A2', 'connections':(
                        [0, 1, DIRECTION_ASCENDING], # d- to e
                    )},
                {'interval':'M2', 'connections':(
                        [1, 2, DIRECTION_ASCENDING], # e to f#
                    )},
                {'interval':'m3', 'connections':(
                        [2, 3, DIRECTION_ASCENDING], # f# to a
                    )},
                {'interval':'M2', 'connections':(
                        [3, 4, DIRECTION_ASCENDING], # a to b
                    )},
                {'interval':'-M2', 'connections':(
                        [4, 5, DIRECTION_ASCENDING], # b to a (downward)
                    )},
                {'interval':'m3', 'connections':(
                        [5, TERMINUS_HIGH, DIRECTION_ASCENDING], # a to c
                    )},

                # descending
                {'interval':'-m2', 'connections':(
                        [TERMINUS_HIGH, 6, DIRECTION_DESCENDING], # c to d- (up)
                    )},
                {'interval':'d3', 'connections':(
                        [6, 7, DIRECTION_DESCENDING], # d- to b
                    )},
                {'interval':'M2', 'connections':(
                        [7, 8, DIRECTION_DESCENDING], # b to a
                    )},
                {'interval':'m3', 'connections':(
                        [8, 9, DIRECTION_DESCENDING], # a to f#
                    )},
                {'interval':'M2', 'connections':(
                        [9, 10, DIRECTION_DESCENDING], # f# to e
                    )},
                {'interval':'A2', 'connections':(
                        [10, 11, DIRECTION_DESCENDING], # e to d-
                    )},
                {'interval':'m2', 'connections':(
                        [11, TERMINUS_LOW, DIRECTION_DESCENDING], # d- to c
                    )},
                )

        self._net = intervalNetwork.BoundIntervalNetwork(
                        octaveDuplicating=self.octaveDuplicating)
        # using representation stored in interval network
        self._net.fillArbitrary(nodes, edges)





class AbstractWeightedHexatonicBlues(AbstractScale):
    '''A dynamic, probabilistic mixture of minor pentatonic and a hexatonic blues scale
    '''
    def __init__(self):
        AbstractScale.__init__(self)
        self.type = 'Abstract Weighted Hexactonic Blues'
        # probably not, as all may not have some pitches in each octave
        self.octaveDuplicating = True 
        self.deterministic = False
        self._buildNetwork()

    def _buildNetwork(self):
        self.tonicDegree = 1
        self.dominantDegree = 5
        nodes = ({'id':'terminusLow', 'degree':1}, # c
                 {'id':0, 'degree':2}, # e-
                 {'id':1, 'degree':3}, # f
                 {'id':2, 'degree':4}, # f#
                 {'id':3, 'degree':5}, # g
                 {'id':4, 'degree':6}, # b-
                 {'id':'terminusHigh', 'degree':7}, # c
                )
        edges = (
                # all bidirectional
                {'interval':'m3', 'connections':(
                        [TERMINUS_LOW, 0, DIRECTION_BI], # c to e-
                    )},
                {'interval':'M2', 'connections':(
                        [0, 1, DIRECTION_BI], # e- to f
                    )},
                {'interval':'M2', 'connections':(
                        [1, 3, DIRECTION_BI], # f to g
                    )},
                {'interval':'a1', 'connections':(
                        [1, 2, DIRECTION_BI], # f to f#
                    )},
                {'interval':'m2', 'connections':(
                        [2, 3, DIRECTION_BI], # f# to g
                    )},
                {'interval':'m3', 'connections':(
                        [3, 4, DIRECTION_BI], # g to b-
                    )},
                {'interval':'M2', 'connections':(
                        [4, TERMINUS_HIGH, DIRECTION_BI], # b- to c
                    )},
                )

        self._net = intervalNetwork.BoundIntervalNetwork(
                        octaveDuplicating=self.octaveDuplicating, 
                        deterministic=self.deterministic)
        # using representation stored in interval network
        self._net.fillArbitrary(nodes, edges)







#-------------------------------------------------------------------------------
class ConcreteScale(Scale):
    '''
    A concrete scale is specific scale formation with 
    a defined pitch collection (a `tonic` Pitch) that 
    may or may not be bound by specific range. For 
    example, a specific Major Scale, such as G 
    Major, from G2 to G4.

    This class is can either be used directly or more
    commonly as a base class for all concrete scales.
    
    Here we treat a diminished triad as a scale:
    
    
    >>> from music21 import *
    >>> myscale = scale.ConcreteScale(pitches = ["C4", "E-4", "G-4", "A4"])
    >>> myscale.getTonic()
    C4
    >>> myscale.next("G-2")
    A2
    >>> myscale.getPitches("E-5","G-7")
    [E-5, G-5, A5, C6, E-6, G-6, A6, C7, E-7, G-7]
    
    
    A scale that lasts two octaves and uses quarter tones (D~)
    
    
    >>> from music21 import *
    >>> complexscale = scale.ConcreteScale(pitches = ["C#3", "E-3", "F3", "G3", "B3", "D~4", "F#4", "A4", "C#5"])
    >>> complexscale.getTonic()
    C#3
    >>> complexscale.next("G3", direction=scale.DIRECTION_DESCENDING)
    F3
    >>> complexscale.getPitches("C3","C7")
    [C#3, E-3, F3, G3, B3, D~4, F#4, A4, C#5, E-5, F5, G5, B5, D~6, F#6, A6]
    >>> complexscale.getPitches("C7","C5")
    [A6, F#6, D~6, B5, G5, F5, E-5, C#5]
    
    
    
    '''

    isConcrete = True

    def __init__(self, tonic=None, pitches = None):
        Scale.__init__(self)

        self.type = 'Concrete'
        # store an instance of an abstract scale
        # subclasses might use multiple abstract scales?
        self._abstract = None

        # determine whether this is a limited range
        self.boundRange = False

        if tonic is None and pitches is not None and common.isListLike(pitches) and len(pitches) > 0:
            tonic = pitches[0]

        # here, tonic is a pitch
        # the abstract scale defines what step the tonic is expected to be 
        # found on
        # no default tonic is defined; as such, it is mostly an abstract scale
        if tonic is None:
            self._tonic = None #pitch.Pitch()
        elif common.isStr(tonic):
            self._tonic = pitch.Pitch(tonic)
        elif hasattr(tonic, 'classes') and 'GeneralNote' in tonic.classes:
            self._tonic = tonic.pitch
        else: # assume this is a pitch object
            self._tonic = tonic

        if pitches is not None and common.isListLike(pitches) and len(pitches) > 0:
            self._abstract = AbstractScale()
            self._abstract.buildNetworkFromPitches(pitches)
            if tonic in pitches:
                self._abstract.tonicDegree = pitches.index(tonic) + 1
            

    def _isConcrete(self):
        '''
        To be concrete, a Scale must have a 
        defined tonic. An abstract Scale is not Concrete
        '''
        if self._tonic is None:
            return False
        else:
            return True

    isConcrete = property(_isConcrete, 
        doc = '''Return True if the scale is Concrete, that is, it has a defined Tonic. 

        >>> from music21 import *
        >>> sc1 = scale.MajorScale('c')
        >>> sc1.isConcrete
        True
        >>> sc2 = scale.MajorScale()    
        >>> sc2.isConcrete
        False

        ''')


    def __eq__(self, other):
        '''For concrete equality, the stored abstract objects must evaluate as equal, as well as local attributes. 

        >>> from music21 import *
        >>> sc1 = scale.MajorScale('c')
        >>> sc2 = scale.MajorScale('c')
        >>> sc3 = scale.MinorScale('c')
        >>> sc4 = scale.MajorScale('g')
        >>> sc5 = scale.MajorScale() # an abstract scale, as no tonic defined

        >>> sc1 == sc2
        True
        >>> sc1 == sc3
        False
        >>> sc1 == sc4
        False
        >>> sc1.abstract == sc4.abstract # can compare abstract forms
        True
        >>> sc4 == sc5 # implicit abstract comparison
        True
        >>> sc5 == sc2 # implicit abstract comparison
        True
        >>> sc5 == sc3 # implicit abstract comparison
        False

        '''
        # have to test each so as not to confuse with a subclass
        # TODO: add pitch range comparison if defined
        if other is None:
            return False
        if (not hasattr(self, 'isConcrete')) or (not hasattr(other, 'isConcrete')):
            return False
        
        if not self.isConcrete or not other.isConcrete:
            # if tonic is none, then we automatically do an abstract comparison
            return self._abstract == other._abstract
        
        else:
            if (isinstance(other, self.__class__) and 
                isinstance(self, other.__class__) and 
                self._abstract == other._abstract and
                self.boundRange == other.boundRange and
                self._tonic == other._tonic 
                ):
                return True     
            else:
                return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def _getName(self):
        '''
        Return or construct the name of this scale
        '''
        if self._tonic is None:
            return " ".join(['Abstract', self.type]) 
        else:
            return " ".join([self._tonic.name, self.type]) 

    name = property(_getName, 
        doc = '''Return or construct the name of this scale.

        >>> from music21 import *
        >>> sc = scale.DiatonicScale() # abstract, as no defined tonic
        >>> sc.name
        'Abstract Diatonic'
        ''')

    def __repr__(self):
        return '<music21.scale.%s %s %s>' % (self.__class__.__name__, self._tonic.name, self.type)


    #---------------------------------------------------------------------------
    def getTonic(self):
        '''Return the tonic. 

        >>> from music21 import *
        >>> sc = scale.ConcreteScale(tonic = 'e-4')
        >>> sc.getTonic()
        E-4
        '''
        return self._tonic

    def _getAbstract(self):
        '''Return the underlying abstract scale
        '''
        # copy before returning?
        return self._abstract

    abstract = property(_getAbstract, 
        doc='''Return the AbstractScale instance governing this ConcreteScale.

        >>> from music21 import *
        >>> sc1 = scale.MajorScale('d')
        >>> sc2 = scale.MajorScale('b-')
        >>> sc1 == sc2
        False
        >>> sc1.abstract == sc2.abstract
        True
        ''')

    def getDegreeMaxUnique(self):
        '''Convenience routine to get this from the AbstractScale.
        '''
        return self._abstract.getDegreeMaxUnique()

    def transpose(self, value, inPlace=False):
        '''
        Transpose this Scale by the given interval

        note: it does not makes sense to transpose an abstract scale;
        thus, only concrete scales can be transposed.

        >>> from music21 import *
        >>> sc1 = scale.MajorScale('C')
        >>> sc2 = sc1.transpose('p5')
        >>> sc2
        <music21.scale.MajorScale G major>
        >>> sc3 = sc2.transpose('p5')
        >>> sc3
        <music21.scale.MajorScale D major>
        ''' 
        if inPlace:
            post = self
        else:
            post = copy.deepcopy(self)
        if self._tonic is None:
            # could raise an error; just assume a 'c'
            post._tonic = pitch.Pitch('C4')
            post._tonic.transpose(value, inPlace=True)        
        else:
            post._tonic.transpose(value, inPlace=True)        
        # may need to clear cache here
        return post

    def tune(self, streamObj, minPitch=None, maxPitch=None, direction=None):
        '''
        Given a Stream object containing Pitches, match all pitch names 
        and or pitch space values and replace the target pitch with 
        copies of pitches stored in this scale.


        This is always applied recursively to all sub-Streams. 
        '''
        # we may use a directed or subset of the scale to tune
        # in the future, we might even match contour or direction
        pitchColl = self.getPitches(minPitch=minPitch, maxPitch=maxPitch,
                    direction=direction)
        pitchCollNames = [p.name for p in pitchColl]
        #for p in streamObj.pitches: # this is always recursive
        for e in streamObj.flat.notes: # get notes and chords

            if e.isChord:
                src = e.pitches
            else: # simulate a lost
                src = [e.pitch]

            dst = [] # store dst in a list of resetting chord pitches
            for p in src:
                # some pitches might be quarter / 3/4 tones; need to convert
                # these to microtonal representations so that we can directly
                # compare pitch names
                pAlt = p.convertQuarterTonesToMicrotones(inPlace=False)
                # need to permit enharmonic comparisons: G# and A- should 
                # in most cases match
                testEnharmonics = pAlt.getAllCommmonEnharmonics(alterLimit=2)
                testEnharmonics.append(pAlt)
                for pEnh in testEnharmonics:
                    if pEnh.name in pitchCollNames:
                        # get the index from the names and extract the pitch by
                        # index
                        pDst = pitchColl[pitchCollNames.index(pEnh.name)]
                        # get a deep copy for each note
                        pDstNew = copy.deepcopy(pDst)
                        pDstNew.octave = pEnh.octave # copy octave
                        # need to adjust enharmonic
                        pDstNewEnh = pDstNew.getAllCommmonEnharmonics(
                                     alterLimit=2)
                        match = None
                        for x in pDstNewEnh:
                            # try to match enharmonic with original alt
                            if x.name == pAlt.name:
                                match = x
                        if match is None: # get original
                            dst.append(pDstNew)
                        else:
                            dst.append(match)
            # reassign the changed pitch
            if len(dst) > 0:
                if e.isChord:
                    # note: we may not have matched all pitches
                    e.pitches = dst
                else: # only one
                    e.pitch = dst[0]



    def romanNumeral(self, degree):
        '''Return a RomanNumeral object built on the specified scale degree.

        >>> from music21 import *
        >>> sc1 = scale.MajorScale('a-4')
        
        >>> h1 = sc1.romanNumeral(1)
        >>> h1.root()
        A-4
        >>> h5 = sc1.romanNumeral(5)
        >>> h5.root()
        E-5
        >>> h5
        <music21.roman.RomanNumeral V>
        '''
        from music21 import roman
        return roman.RomanNumeral(degree, self)



    def getPitches(self, minPitch=None, maxPitch=None, 
        direction=None):
        '''
        Return a list of Pitch objects, using a 
        deepcopy of a cached version if available. 

        '''
        # get from interval network of abstract scale

        if self._abstract is not None:
            # TODO: get and store in cache; return a copy
            # or generate from network stored in abstract
            if self._tonic is None:
                # note: could raise an error here, but instead will
                # use a pseudo-tonic
                pitchObj = pitch.Pitch('C4')
            else:
                pitchObj = self._tonic
            stepOfPitch = self._abstract.tonicDegree

            if common.isStr(minPitch):
                minPitch = pitch.Pitch(minPitch)
            if common.isStr(maxPitch):
                maxPitch = pitch.Pitch(maxPitch)
            

            if minPitch > maxPitch and direction is None:
                reverse = True
                (minPitch, maxPitch) = (maxPitch, minPitch)
            elif direction == DIRECTION_DESCENDING:
                reverse = True # reverse presentation so pitches go high to low
            else:
                reverse = False

            if direction is None:
                direction = DIRECTION_ASCENDING


            # this creates new pitches on each call
            return self._abstract.getRealization(pitchObj, 
                        stepOfPitch, 
                        minPitch=minPitch, maxPitch=maxPitch, 
                        direction=direction,
                        reverse=reverse)
        else:
            return []
        #raise ScaleException("Cannot generate a scale from a DiatonicScale class")

    pitches = property(getPitches, 
        doc ='''Get a default pitch list from this scale.
        ''')

    def getChord(self, minPitch=None, maxPitch=None, 
        direction=DIRECTION_ASCENDING, **keywords):
        '''
        Return a realized chord containing all the 
        pitches in this scale within a particular 
        inclusive range defined by two pitches.

        All keyword arguments are passed on to the 
        Chord, permitting specification of 
        `quarterLength` and similar parameters.
        '''
        from music21 import chord
        return chord.Chord(self.getPitches(minPitch=minPitch, maxPitch=maxPitch, direction=direction), **keywords)

    chord = property(getChord, 
        doc = '''Return a Chord object from this harmony over a default range.  
        Use the `getChord()` method if you need greater control over the
        parameters of the chord.
        ''')

    def pitchFromDegree(self, degree, minPitch=None, maxPitch=None, 
        direction=DIRECTION_ASCENDING, equateTermini=True):        
        '''
        Given a scale degree, return a deepcopy of the appropriate pitch. 

        >>> from music21 import *
        >>> sc = scale.MajorScale('e-')
        >>> sc.pitchFromDegree(2)
        F4
        >>> sc.pitchFromDegree(7)
        D5
        
        OMIT_FROM_DOCS
        Test deepcopy
        >>> d = sc.pitchFromDegree(7)
        >>> d.accidental = pitch.Accidental('sharp')
        >>> d
        D#5
        >>> sc.pitchFromDegree(7)
        D5
        
        
        '''
        post = self._abstract.getPitchFromNodeDegree(
            pitchReference=self._tonic, # pitch defined here
            nodeName=self._abstract.tonicDegree, # defined in abstract class
            nodeDegreeTarget=degree, # target looking for
            direction=direction, 
            minPitch=minPitch, 
            maxPitch=maxPitch, 
            equateTermini=equateTermini)
        return post

#         if 0 < degree <= self._abstract.getDegreeMaxUnique(): 
#             return self.getPitches()[degree - 1]
#         else: 
#             raise("Scale degree is out of bounds: must be between 1 and %s." % self._abstract.getDegreeMaxUnique())


    def pitchesFromScaleDegrees(self, degreeTargets, minPitch=None, 
        maxPitch=None, direction=DIRECTION_ASCENDING):        
        '''
        Given one or more scale degrees, return a list 
        of all matches over the entire range. 


        >>> from music21 import *
        >>> sc = scale.MajorScale('e-')
        >>> sc.pitchesFromScaleDegrees([3,7])
        [G4, D5]
        >>> sc.pitchesFromScaleDegrees([3,7], 'c2', 'c6')
        [D2, G2, D3, G3, D4, G4, D5, G5]

        >>> sc = scale.HarmonicMinorScale('a')
        >>> sc.pitchesFromScaleDegrees([3,7], 'c2', 'c6')
        [C2, G#2, C3, G#3, C4, G#4, C5, G#5, C6]
        '''
        # TODO: rely here on intervalNetwork for caching
        post = self._abstract.realizePitchByDegree(
            pitchReference=self._tonic, # pitch defined here
            nodeId=self._abstract.tonicDegree, # defined in abstract class
            nodeDegreeTargets=degreeTargets, # target looking for
            direction=direction, 
            minPitch=minPitch, 
            maxPitch=maxPitch)
        return post


    def intervalBetweenDegrees(self, degreeStart, degreeEnd, 
        direction=DIRECTION_ASCENDING, equateTermini=True):
        '''
        Given two degrees, provide the interval as an interval.Interval object.


        >>> from music21 import *
        >>> sc = scale.MajorScale('e-')
        >>> sc.intervalBetweenDegrees(3, 7)
        <music21.interval.Interval P5>

        '''
        # get pitches for each degree
        pStart = self.pitchFromDegree(degreeStart, direction=direction, 
                equateTermini=equateTermini)
        pEnd = self.pitchFromDegree(degreeEnd, direction=direction, 
                equateTermini=equateTermini)
        if pStart is None:
            raise ScaleException('cannot get a pitch for scale degree: %s' % pStart)
        elif pEnd is None:
            raise ScaleException('cannot get a pitch for scale degree: %s' % pStart)
        return interval.Interval(pStart, pEnd)

    def getScaleDegreeFromPitch(self, pitchTarget, 
            direction=DIRECTION_ASCENDING, comparisonAttribute='name'):
        '''
        For a given pitch, return the appropriate scale degree. 
        If no scale degree is available, None is returned.


        Note -- by default it will find based on note name not on 
        PitchClass because this is used so commonly by tonal functions.
        So if it's important that D# and E- are the same, set the
        comparisonAttribute to `pitchClass`
        

        >>> from music21 import *
        >>> sc = scale.MajorScale('e-')
        >>> sc.getScaleDegreeFromPitch('e-2')
        1
        >>> sc.getScaleDegreeFromPitch('d')
        7
        >>> sc.getScaleDegreeFromPitch('d#', comparisonAttribute='name') == None
        True
        >>> sc.getScaleDegreeFromPitch('d#', comparisonAttribute='pitchClass')
        1


        >>> sc = scale.HarmonicMinorScale('a')
        >>> sc.getScaleDegreeFromPitch('c')
        3
        >>> sc.getScaleDegreeFromPitch('g#')
        7
        >>> sc.getScaleDegreeFromPitch('g')
        '''

        post = self._abstract.getRelativeNodeDegree(
            pitchReference=self._tonic, 
            nodeName=self._abstract.tonicDegree, 
            pitchTarget=pitchTarget,      
            comparisonAttribute=comparisonAttribute, 
            direction=direction)
        return post


    def next(self, pitchOrigin=None, direction='ascending', stepSize=1, 
        getNeighbor=True):
        '''
        Get the next pitch above (or if direction is 'descending', below) 
        a `pitchOrigin` or None. If the `pitchOrigin` is None, the tonic pitch is 
        returned. This is useful when starting a chain of iterative calls. 


        The `direction` attribute may be either ascending or descending. 
        Default is `ascending`. Optionally, positive or negative integers 
        may be provided as directional stepSize scalars.


        An optional `stepSize` argument can be used to set the number 
        of scale steps that are stepped through.  Thus, .next(stepSize=2)
        will give not the next pitch in the scale, but the next after this one.
        

        The `getNeighbor` will return a pitch from the scale 
        if `pitchOrigin` is not in the scale. This value can be 
        True, 'ascending', or 'descending'.


        >>> from music21 import *
        >>> sc = scale.MajorScale('e-')
        >>> sc.next('e-5')
        F5
        >>> sc.next('e-5', stepSize=2)
        G5
        >>> sc.next('e-6', stepSize=3)
        A-6
        
        
        This uses the getNeighbor attribute to 
        find the next note above f#5 in the E-flat
        major scale:
        
        
        >>> sc.next('f#5')
        G5


        >>> from music21 import *
        >>> sc = scale.HarmonicMinorScale('g')
        >>> sc.next('g4', 'descending')
        F#4
        >>> sc.next('F#4', 'descending')
        E-4
        >>> sc.next('E-4', 'descending')
        D4
        >>> sc.next('E-4', 'ascending', 1)
        F#4
        >>> sc.next('E-4', 'ascending', 2)
        G4
        '''
        if pitchOrigin is None:
            return self._tonic

        # allow numerical directions
        if common.isNum(direction):
            if direction != 0:
                # treat as a positive or negative step scalar
                if direction > 0:
                    stepScalar = direction
                    direction = DIRECTION_ASCENDING
                else: # negative non-zero
                    stepScalar = abs(direction)
                    direction = DIRECTION_DESCENDING
            else:
                raise ScaleException('direction cannot be zero')
        else: # when direction is a string, use scalar of 1
            stepScalar = 1 

        # pick reverse direction for neighbor
        if getNeighbor is True:
            if direction in [DIRECTION_ASCENDING]:
                getNeighbor = DIRECTION_DESCENDING
            elif direction in [DIRECTION_DESCENDING]:
                getNeighbor = DIRECTION_ASCENDING

        post = self._abstract.nextPitch(
            pitchReference=self._tonic, 
            nodeName=self._abstract.tonicDegree, 
            pitchOrigin=pitchOrigin,      
            direction=direction,
            stepSize = stepSize*stepScalar, # multiplied
            getNeighbor=getNeighbor
            )
        return post


    def isNext(self, other, pitchOrigin, direction='ascending', stepSize=1, 
        getNeighbor=True, comparisonAttribute='name'):
        '''Given another pitch, as well as an origin and a direction, determine if this other pitch is in the next in the scale.

        >>> from music21 import *
        >>> sc1 = scale.MajorScale('g')
        >>> sc1.isNext('d4', 'c4', 'ascending')
        True
        '''
        if common.isStr(other): # convert to pitch
            other = pitch.Pitch(other)
        elif hasattr(other, 'pitch'): # possibly a note
            other = other.pitch # just get pitch component
        elif not isinstance(other, pitch.Pitch):
            return False # cannot compare to nonpitch

        nPitch = self.next(pitchOrigin, direction=direction, stepSize=stepSize, 
                 getNeighbor=getNeighbor) 
        if nPitch is None:
            return None

        if (getattr(nPitch, comparisonAttribute) == 
            getattr(other, comparisonAttribute)):
            return True
        else:
            return False



    #---------------------------------------------------------------------------
    # comparison and evaluation

    def match(self, other, comparisonAttribute='pitchClass'):
        '''Given another object of various forms (e.g., a :class:`~music21.stream.Stream`, a :class:`~music21.scale.ConcreteScale`, a list of :class:`~music21.pitch.Pitch` objects), return a named dictionary of pitch lists with keys 'matched' and 'notMatched'.

        >>> from music21 import *
        >>> sc1 = scale.MajorScale('g')
        >>> sc2 = scale.MajorScale('d')
        >>> sc3 = scale.MajorScale('a')
        >>> sc4 = scale.MajorScale('e')
        >>> sc1.match(sc2)
        {'notMatched': [C#5], 'matched': [D4, E4, F#4, G4, A4, B4, D5]}
        >>> sc2.match(sc3)
        {'notMatched': [G#5], 'matched': [A4, B4, C#5, D5, E5, F#5, A5]}

        >>> sc1.match(sc4)
        {'notMatched': [G#4, C#5, D#5], 'matched': [E4, F#4, A4, B4, E5]}

        '''
        # strip out unique pitches in a list
        otherPitches = self._extractPitchList(other,
                        comparisonAttribute=comparisonAttribute)

        # need to deal with direction here? or get an aggregate scale
        matched, notMatched = self._abstract._net.match(
            pitchReference=self._tonic, 
            nodeId=self._abstract.tonicDegree, 
            pitchTarget=otherPitches, # can supply a list here
            comparisonAttribute=comparisonAttribute)

        post = {}
        post['matched'] = matched
        post['notMatched'] = notMatched
        return post



    def findMissing(self, other, comparisonAttribute='pitchClass', 
        minPitch=None, maxPitch=None, direction=DIRECTION_ASCENDING,
        alteredDegrees={}):
        '''Given another object of various forms (e.g., a :class:`~music21.stream.Stream`, a :class:`~music21.scale.ConcreteScale`, a list of :class:`~music21.pitch.Pitch` objects), return a list of pitches that are found in this Scale but are not found in the provided object. 

        >>> from music21 import *
        >>> sc1 = scale.MajorScale('g4')
        >>> sc1.findMissing(['d'])
        [G4, A4, B4, C5, E5, F#5, G5]
        '''
        # strip out unique pitches in a list
        otherPitches = self._extractPitchList(other,
                        comparisonAttribute=comparisonAttribute)
        post = self._abstract._net.findMissing(
            pitchReference=self._tonic, 
            nodeId=self._abstract.tonicDegree, 
            pitchTarget=otherPitches, # can supply a list here
            comparisonAttribute=comparisonAttribute,
            minPitch=minPitch, maxPitch=maxPitch, direction=direction,
            alteredDegrees=alteredDegrees,
            )
        return post        



    def deriveRanked(self, other, resultsReturned=4,
         comparisonAttribute='pitchClass'):
        '''Return a list of closest-matching :class:`~music21.scale.ConcreteScale` objects based on this :class:`~music21.scale.AbstractScale`, provided as a :class:`~music21.stream.Stream`, a :class:`~music21.scale.ConcreteScale`, or a list of :class:`~music21.pitch.Pitch` objects. Returned integer values represent the number of mathces. 

        >>> from music21 import *
        >>> sc1 = scale.MajorScale()
        >>> sc1.deriveRanked(['c', 'e', 'b'])
        [(3, <music21.scale.MajorScale G major>), (3, <music21.scale.MajorScale C major>), (2, <music21.scale.MajorScale B major>), (2, <music21.scale.MajorScale A major>)]

        >>> sc1.deriveRanked(['c', 'e', 'e', 'e', 'b'])
        [(5, <music21.scale.MajorScale G major>), (5, <music21.scale.MajorScale C major>), (4, <music21.scale.MajorScale B major>), (4, <music21.scale.MajorScale A major>)]

        >>> sc1.deriveRanked(['c#', 'e', 'g#'])
        [(3, <music21.scale.MajorScale B major>), (3, <music21.scale.MajorScale A major>), (3, <music21.scale.MajorScale E major>), (3, <music21.scale.MajorScale C- major>)]


        '''
        # possibly return dictionary with named parameters
        # default return all scales that match all provided pitches
        # instead of results returned, define how many matched pitches necessary
        otherPitches = self._extractPitchList(other,
                        comparisonAttribute=comparisonAttribute)

        pairs = self._abstract._net.find(pitchTarget=otherPitches,
                             resultsReturned=resultsReturned,
                             comparisonAttribute=comparisonAttribute)
        post = []
        for weight, p in pairs:
            sc = self.__class__(tonic=p)
            post.append((weight, sc))
        return post


    def derive(self, other, comparisonAttribute='pitchClass'):
        '''Return the closest-matching :class:`~music21.scale.ConcreteScale` based on the pitch collection provided as a :class:`~music21.stream.Stream`, a :class:`~music21.scale.ConcreteScale`, or a list of :class:`~music21.pitch.Pitch` objects.

        >>> from music21 import *
        >>> sc1 = scale.MajorScale()
        >>> sc1.derive(['c#', 'e', 'g#'])
        <music21.scale.MajorScale B major>
        >>> sc1.derive(['e-', 'b-', 'd'], comparisonAttribute='name')
        <music21.scale.MajorScale B- major>
        '''
        otherPitches = self._extractPitchList(other,
                        comparisonAttribute=comparisonAttribute)

        # weight target membership
        pairs = self._abstract._net.find(pitchTarget=otherPitches,
                            comparisonAttribute=comparisonAttribute)

        return self.__class__(tonic=pairs[0][1])



    def deriveByDegree(self, degree, pitch):
        '''Given a scale degree and a pitch, return a new :class:`~music21.scale.ConcreteScale` that satisfies that condition.

        >>> from music21 import *
        >>> sc1 = scale.MajorScale()
        >>> sc1.deriveByDegree(7, 'c') # what scale has c as its 7th degree
        <music21.scale.MajorScale D- major>

        '''
        # TODO: this does not work for directional scales yet
        # weight target membership
        p = self._abstract.getNewTonicPitch(pitchReference=pitch, 
            nodeName=degree)
        if p is None:
            raise ScaleException('cannot derive new tonic')
        
        return self.__class__(tonic=p)


    #---------------------------------------------------------------------------
    # alternative outputs


    def getScalaStorage(self):
        '''Return a configured scale scale object
        '''
        ss = self.abstract.getScalaStorage()
        # customize with more specific representation
        ss.description = self.__repr__()
        return ss


    def write(self, fmt=None, fp=None, direction=DIRECTION_ASCENDING):
        '''Write the scale in a format. Here, prepare scala format if requested.
        '''
        if fmt is not None:
            format, ext = common.findFormat(fmt)
            if format in ['scala']:
                return self.abstract.write(fmt=fmt, fp=fp, direction=direction)
        return Scale.write(self, fmt=fmt, fp=fp)


    def show(self, fmt=None, app=None, direction=DIRECTION_ASCENDING):
        '''Show the scale in a format. Here, prepare scala format if requested.
        '''
        if fmt is not None:
            format, ext = common.findFormat(fmt)
            if format in ['scala']:
                self.abstract.show(fmt=fmt, app=app, direction=direction)
                return
        Scale.show(self, fmt=fmt, app=app)


    def _getMusicXML(self):
        '''Return a complete musicxml representation as an xml string. This must call _getMX to get basic mxNote objects

        >>> from music21 import *
        '''
        from music21 import stream, note
        m = stream.Measure()
        for i in range(1, self._abstract.getDegreeMaxUnique()+1):
            p = self.pitchFromDegree(i)
            n = note.Note()
            n.pitch = p
            if i == 1:
                n.addLyric(self.name)

            if p.name == self.getTonic().name:
                n.quarterLength = 4 # set longer
            else:
                n.quarterLength = 1
            m.append(n)
        m.timeSignature = m.bestTimeSignature()
        return musicxmlTranslate.measureToMusicXML(m)

    musicxml = property(_getMusicXML, 
        doc = '''Return a complete musicxml representation.
        ''')    





#-------------------------------------------------------------------------------
# concrete scales and subclasses


class DiatonicScale(ConcreteScale):
    '''A concrete diatonic scale. Each DiatonicScale has one instance of a  :class:`~music21.scale.AbstractDiatonicScale`.
    '''
    def __init__(self, tonic=None):
        ConcreteScale.__init__(self, tonic=tonic)
        self._abstract = AbstractDiatonicScale()
        self.type = 'Diatonic'

    def getTonic(self):
        '''Return the tonic. 

        >>> from music21 import *
        >>> sc = scale.MajorScale('e-')
        >>> sc.getDominant()
        B-4
        >>> sc = scale.MajorScale('F#')
        >>> sc.getDominant()
        C#5
        '''
        # NOTE: override method on ConcreteScale that simply returns _tonic
        return self.pitchFromDegree(self._abstract.tonicDegree)

    def getDominant(self):
        '''Return the dominant. 

        >>> from music21 import *
        >>> sc = scale.MajorScale('e-')
        >>> sc.getDominant()
        B-4
        >>> sc = scale.MajorScale('F#')
        >>> sc.getDominant()
        C#5
        '''
        return self.pitchFromDegree(self._abstract.dominantDegree)
    

    def getLeadingTone(self):
        '''Return the leading tone. 

        >>> from music21 import *
        >>> sc = scale.MinorScale('c')
        >>> sc.pitchFromDegree(7)
        B-4
        >>> sc.getLeadingTone()
        B4
        >>> sc.getDominant()
        G4

        '''
        # NOTE: must be adjust for modes that do not have a proper leading tone
        interval1to7 = interval.notesToInterval(self._tonic, 
                        self.pitchFromDegree(7))
        if interval1to7.name != 'M7':
            # if not a major seventh from the tonic, get a pitch a M7 above
            return interval.transposePitch(self.pitchFromDegree(1), "M7")
        else:
            return self.pitchFromDegree(7)


    def getParallelMinor(self):
        '''Return a parallel minor scale based on this concrete major scale.

        >>> from music21 import *
        >>> sc1 = scale.MajorScale(pitch.Pitch('a'))
        >>> sc1.pitches
        [A4, B4, C#5, D5, E5, F#5, G#5, A5]
        >>> sc2 = sc1.getParallelMinor()
        >>> sc2.pitches
        [A4, B4, C5, D5, E5, F5, G5, A5]
        '''
        return MinorScale(self._tonic)


    def getParallelMajor(self):
        '''Return a concrete relative major scale

        >>> from music21 import *
        >>> sc1 = scale.MinorScale(pitch.Pitch('g'))
        >>> sc1.pitches
        [G4, A4, B-4, C5, D5, E-5, F5, G5]
        >>> sc2 = sc1.getParallelMajor()
        >>> sc2.pitches
        [G4, A4, B4, C5, D5, E5, F#5, G5]
        '''
        return MajorScale(self._tonic)



    def getRelativeMinor(self):
        '''Return a relative minor scale based on this concrete major scale.

        >>> sc1 = MajorScale(pitch.Pitch('a'))
        >>> sc1.pitches
        [A4, B4, C#5, D5, E5, F#5, G#5, A5]
        >>> sc2 = sc1.getRelativeMinor()
        >>> sc2.pitches
        [F#5, G#5, A5, B5, C#6, D6, E6, F#6]
        '''
        return MinorScale(self.pitchFromDegree(self.abstract.relativeMinorDegree))


    def getRelativeMajor(self):
        '''Return a concrete relative major scale

        >>> sc1 = MinorScale(pitch.Pitch('g'))
        >>> sc1.pitches
        [G4, A4, B-4, C5, D5, E-5, F5, G5]
        >>> sc2 = sc1.getRelativeMajor()
        >>> sc2.pitches
        [B-4, C5, D5, E-5, F5, G5, A5, B-5]

        >>> sc2 = DorianScale('d')
        >>> sc2.getRelativeMajor().pitches
        [C5, D5, E5, F5, G5, A5, B5, C6]
        '''
        return MajorScale(self.pitchFromDegree(self.abstract.relativeMajorDegree))



    def _getMusicXML(self):
        '''Return a complete musicxml representation as an xml string. This must call _getMX to get basic mxNote objects

        >>> from music21 import *
        '''
        # note: overidding behavior on 
        from music21 import stream, note
        m = stream.Measure()
        for i in range(1, self._abstract.getDegreeMaxUnique()+1):
            p = self.pitchFromDegree(i)
            n = note.Note()
            n.pitch = p
            if i == 1:
                n.addLyric(self.name)

            if p.name == self.getTonic().name:
                n.quarterLength = 4 # set longer
            elif p.name == self.getDominant().name:
                n.quarterLength = 2 # set longer
            else:
                n.quarterLength = 1
            m.append(n)
        m.timeSignature = m.bestTimeSignature()
        return musicxmlTranslate.measureToMusicXML(m)

    musicxml = property(_getMusicXML, 
        doc = '''Return a complete musicxml representation.
        ''')    



#-------------------------------------------------------------------------------
# diatonic scales and modes
class MajorScale(DiatonicScale):
    '''A Major Scale

    >>> sc = MajorScale(pitch.Pitch('d'))
    >>> sc.pitchFromDegree(7).name
    'C#'
    '''
    
    def __init__(self, tonic=None):

        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "major"
        # build the network for the appropriate scale
        self._abstract._buildNetwork(self.type)

class MinorScale(DiatonicScale):
    '''A natural minor scale, or the Aeolian mode.

    >>> sc = MinorScale(pitch.Pitch('g'))
    >>> sc.pitches
    [G4, A4, B-4, C5, D5, E-5, F5, G5]
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "minor"
        self._abstract._buildNetwork(self.type)


class DorianScale(DiatonicScale):
    '''A natural minor scale, or the Aeolian mode.

    >>> sc = DorianScale(pitch.Pitch('d'))
    >>> sc.pitches
    [D4, E4, F4, G4, A4, B4, C5, D5]
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "dorian"
        self._abstract._buildNetwork(self.type)


class PhrygianScale(DiatonicScale):
    '''A phrygian scale

    >>> sc = PhrygianScale(pitch.Pitch('e'))
    >>> sc.pitches
    [E4, F4, G4, A4, B4, C5, D5, E5]
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "phrygian"
        self._abstract._buildNetwork(self.type)


class LydianScale(DiatonicScale):
    '''A lydian scale

    >>> sc = LydianScale(pitch.Pitch('f'))
    >>> sc.pitches
    [F4, G4, A4, B4, C5, D5, E5, F5]
    >>> sc = LydianScale(pitch.Pitch('c'))
    >>> sc.pitches
    [C4, D4, E4, F#4, G4, A4, B4, C5]
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "lydian"
        self._abstract._buildNetwork(self.type)

class MixolydianScale(DiatonicScale):
    '''A mixolydian scale

    >>> sc = MixolydianScale(pitch.Pitch('g'))
    >>> sc.pitches
    [G4, A4, B4, C5, D5, E5, F5, G5]
    >>> sc = MixolydianScale(pitch.Pitch('c'))
    >>> sc.pitches
    [C4, D4, E4, F4, G4, A4, B-4, C5]
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "mixolydian"
        self._abstract._buildNetwork(self.type)


class HypodorianScale(DiatonicScale):
    '''A hypodorian scale

    >>> sc = HypodorianScale(pitch.Pitch('d'))
    >>> sc.pitches
    [A3, B3, C4, D4, E4, F4, G4, A4]
    >>> sc = HypodorianScale(pitch.Pitch('c'))
    >>> sc.pitches
    [G3, A3, B-3, C4, D4, E-4, F4, G4]
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "hypodorian"
        self._abstract._buildNetwork(self.type)


class HypophrygianScale(DiatonicScale):
    '''A hypophrygian scale

    >>> sc = HypophrygianScale(pitch.Pitch('e'))
    >>> sc.abstract.octaveDuplicating
    True
    >>> sc.pitches
    [B3, C4, D4, E4, F4, G4, A4, B4]
    >>> sc.getTonic()
    E4
    >>> sc.getDominant()
    A4
    >>> sc.pitchFromDegree(1) # scale degree 1 is treated as lowest
    B3
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "hypophrygian"
        self._abstract._buildNetwork(self.type)


class HypolydianScale(DiatonicScale):
    '''A hypolydian scale

    >>> sc = HypolydianScale(pitch.Pitch('f'))
    >>> sc.pitches
    [C4, D4, E4, F4, G4, A4, B4, C5]
    >>> sc = HypolydianScale(pitch.Pitch('c'))
    >>> sc.pitches
    [G3, A3, B3, C4, D4, E4, F#4, G4]
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "hypolydian"
        self._abstract._buildNetwork(self.type)


class HypomixolydianScale(DiatonicScale):
    '''A hypolydian scale

    >>> sc = HypomixolydianScale(pitch.Pitch('g'))
    >>> sc.pitches
    [D4, E4, F4, G4, A4, B4, C5, D5]
    >>> sc = HypomixolydianScale(pitch.Pitch('c'))
    >>> sc.pitches
    [G3, A3, B-3, C4, D4, E4, F4, G4]
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "hypomixolydian"
        self._abstract._buildNetwork(self.type)


class LocrianScale(DiatonicScale):
    '''A locrian scale

    >>> sc = LocrianScale(pitch.Pitch('b'))
    >>> sc.pitches
    [B4, C5, D5, E5, F5, G5, A5, B5]
    >>> sc = LocrianScale(pitch.Pitch('c'))
    >>> sc.pitches
    [C4, D-4, E-4, F4, G-4, A-4, B-4, C5]
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "locrian"
        self._abstract._buildNetwork(self.type)


class HypolocrianScale(DiatonicScale):
    '''A hypolocrian scale

    >>> sc = HypolocrianScale(pitch.Pitch('b'))
    >>> sc.pitches
    [F4, G4, A4, B4, C5, D5, E5, F5]
    >>> sc = HypolocrianScale(pitch.Pitch('c'))
    >>> sc.pitches
    [G-3, A-3, B-3, C4, D-4, E-4, F4, G-4]
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "hypolocrian"
        self._abstract._buildNetwork(self.type)


class HypoaeolianScale(DiatonicScale):
    '''A hypoaeolian scale

    >>> sc = HypoaeolianScale(pitch.Pitch('a'))
    >>> sc.pitches
    [E4, F4, G4, A4, B4, C5, D5, E5]
    >>> sc = HypoaeolianScale(pitch.Pitch('c'))
    >>> sc.pitches
    [G3, A-3, B-3, C4, D4, E-4, F4, G4]
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "hypoaeolian"
        self._abstract._buildNetwork(self.type)






#-------------------------------------------------------------------------------
# other diatonic scales
class HarmonicMinorScale(DiatonicScale):
    '''A harmonic minor scale

    >>> sc = HarmonicMinorScale('e4')
    >>> sc.pitches
    [E4, F#4, G4, A4, B4, C5, D#5, E5]
    >>> sc.getTonic()
    E4
    >>> sc.getDominant()
    B4
    >>> sc.pitchFromDegree(1) # scale degree 1 is treated as lowest
    E4
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "harmonic minor"
        
        # note: this changes the previously assigned AbstractDiatonicScale
        # from the DiatonicScale base class

        self._abstract = AbstractHarmonicMinorScale()
        # network building happens on object creation
        #self._abstract._buildNetwork()



class MelodicMinorScale(DiatonicScale):
    '''A melodic minor scale

    >>> sc = MelodicMinorScale('e4')
    '''
    def __init__(self, tonic=None):
        DiatonicScale.__init__(self, tonic=tonic)
        self.type = "melodic minor"
        
        # note: this changes the previously assigned AbstractDiatonicScale
        # from the DiatonicScale base class
        self._abstract = AbstractMelodicMinorScale()




#-------------------------------------------------------------------------------
# other sscales

class OctatonicScale(ConcreteScale):
    '''A concrete Octatonic scale. Two modes
    '''
    def __init__(self, tonic=None, mode=None):
        ConcreteScale.__init__(self, tonic=tonic)
        self._abstract = AbstractOctatonicScale(mode=mode)
        self.type = 'Octatonic'



class OctaveRepeatingScale(ConcreteScale):
    '''A concrete cyclical scale, based on a cycle of intervals. These intervals do not have to be octave completing, and thus may produce scales that do no

    >>> from music21 import *
    >>> sc = scale.OctaveRepeatingScale('c4', ['m3', 'M3']) #
    >>> sc.pitches
    [C4, E-4, G4, C5]
    >>> sc.getPitches('g2', 'g6') 
    [G2, C3, E-3, G3, C4, E-4, G4, C5, E-5, G5, C6, E-6, G6]
    >>> sc.getScaleDegreeFromPitch('c4')
    1
    >>> sc.getScaleDegreeFromPitch('e-')
    2
    '''

    def __init__(self, tonic=None, intervalList=['m2']):
        ConcreteScale.__init__(self, tonic=tonic)
        self._abstract = AbstractOctaveRepeatingScale(mode=intervalList)
        self.type = 'Octave Repeating'





class CyclicalScale(ConcreteScale):
    '''A concrete cyclical scale, based on a cycle of intervals. These intervals do not have to be octave completing, and thus may produce scales that do no

    >>> from music21 import *
    >>> sc = scale.CyclicalScale('c4', 'p5') # can give one list
    >>> sc.pitches
    [C4, G4]
    >>> sc.getPitches('g2', 'g6') 
    [B-2, F3, C4, G4, D5, A5, E6]
    >>> sc.getScaleDegreeFromPitch('g4') # as single interval cycle, all are 1
    1
    >>> sc.getScaleDegreeFromPitch('b-2', direction='bi')
    1
    '''

    def __init__(self, tonic=None, intervalList=['m2']):
        ConcreteScale.__init__(self, tonic=tonic)
        self._abstract = AbstractCyclicalScale(mode=intervalList)
        self.type = 'Cyclical'



class ChromaticScale(ConcreteScale):
    '''A concrete cyclical scale, based on a cycle of half steps. These intervals do not have to be octave completing, and thus may produce scales that do no

    >>> from music21 import *
    >>> sc = scale.ChromaticScale('g2') 
    >>> sc.pitches
    [G2, A-2, A2, B-2, C-3, C3, D-3, D3, E-3, F-3, F3, G-3, G3]
    >>> sc.getPitches('g2', 'g6') 
    [G2, A-2, A2, B-2, C-3, C3, D-3, D3, E-3, F-3, F3, G-3, G3, A-3, A3, B-3, C-4, C4, D-4, D4, E-4, F-4, F4, G-4, G4, A-4, A4, B-4, C-5, C5, D-5, D5, E-5, F-5, F5, G-5, G5, A-5, A5, B-5, C-6, C6, D-6, D6, E-6, F-6, F6, G-6, G6]
    >>> sc.abstract.getDegreeMaxUnique()
    12
    >>> sc.pitchFromDegree(1) 
    G2
    >>> sc.pitchFromDegree(2) 
    A-2
    >>> sc.pitchFromDegree(3) 
    A2
    >>> sc.pitchFromDegree(8) 
    D3
    >>> sc.pitchFromDegree(12) 
    G-3
    >>> sc.getScaleDegreeFromPitch('g2', comparisonAttribute='pitchClass')
    1
    >>> sc.getScaleDegreeFromPitch('F#6', comparisonAttribute='pitchClass')
    12
    '''
    def __init__(self, tonic=None):
        ConcreteScale.__init__(self, tonic=tonic)
        self._abstract = AbstractCyclicalScale(mode=['m2','m2','m2',
            'm2','m2','m2', 'm2','m2','m2','m2','m2','m2'])
        self.type = 'Chromatic'



class WholeToneScale(ConcreteScale):
    '''A concrete whole-tone scale. 

    >>> from music21 import *
    >>> sc = scale.WholeToneScale('g2') 
    >>> sc.pitches
    [G2, A2, B2, C#3, D#3, E#3, G3]
    >>> sc.getPitches('g2', 'g6') 
    [G2, A2, B2, C#3, D#3, E#3, G3, A3, B3, C#4, D#4, E#4, G4, A4, B4, C#5, D#5, E#5, G5, A5, B5, C#6, D#6, E#6, G6]
    >>> sc.abstract.getDegreeMaxUnique()
    6
    >>> sc.pitchFromDegree(1) 
    G2
    >>> sc.pitchFromDegree(2) 
    A2
    >>> sc.pitchFromDegree(6) 
    E#3
    >>> sc.getScaleDegreeFromPitch('g2', comparisonAttribute='pitchClass')
    1
    >>> sc.getScaleDegreeFromPitch('F6', comparisonAttribute='pitchClass')
    6
    '''
    def __init__(self, tonic=None):
        ConcreteScale.__init__(self, tonic=tonic)
        self._abstract = AbstractCyclicalScale(mode=['M2', 'M2',
            'M2', 'M2', 'M2', 'M2'])
        self.type = 'Chromatic'




class SieveScale(ConcreteScale):
    '''A scale created from a Xenakis sieve logical string, based on the :class:`~music21.sieve.Sieve` object definition. The complete period of the sieve is realized as intervals and used to create a scale. 

    >>> from music21 import *
    >>> sc = scale.SieveScale('c4', '3@0') 
    >>> sc.pitches
    [C4, E-4]
    >>> sc = scale.SieveScale('d4', '3@0') 
    >>> sc.pitches
    [D4, F4]
    >>> sc = scale.SieveScale('c2', '(-3@2 & 4) | (-3@1 & 4@1) | (3@2 & 4@2) | (-3 & 4@3)') 
    >>> sc.pitches
    [C2, D2, E2, F2, G2, A2, B2, C3]

    '''
    def __init__(self, tonic=None, sieveString='2@0'):
        ConcreteScale.__init__(self, tonic=tonic)

        self._pitchSieve = sieve.PitchSieve(sieveString)
        #environLocal.printDebug([self._pitchSieve.sieveObject.represent(), self._pitchSieve.getIntervalSequence()])
        # mode here is a list of intervals
        self._abstract = AbstractCyclicalScale(
                         mode=self._pitchSieve.getIntervalSequence())
        self.type = 'Sieve'





class ScalaScale(ConcreteScale):
    '''A scale created from a Scala scale .scl file. Any file in the Scala archive can be given by name. Additionally, a file path to a Scala .scl file, or a raw string representation, can be used. 

    >>> sc = ScalaScale('g4', 'mbira banda')
    >>> sc.pitches
    [G4, A4(-15c), B4(-11c), C#5(-7c), D~5(+6c), E5(+14c), F~5(+1c), A-5(+2c)]

    '''
    def __init__(self, tonic=None, scalaString=None):
        ConcreteScale.__init__(self, tonic=tonic)

        self._scalaStorage = None
        self.description = None

        # this might be a raw scala file list
        if scalaString is not None and scalaString.count('\n') > 3:
            # if no match, this might be a complete Scala string
            self._scalaStorage = scala.ScalaStorage(scalaString)
            self._scalaStorage.parse()
        elif scalaString is not None:
            # try to load a named scale from a file path or stored
            # on the scala archive
            # returns None or a scala storage object
            self._scalaStorage = scala.parse(scalaString)
        else: # grab a default
            self._scalaStorage = scala.parse('fj-12tet.scl')    
        self._abstract = AbstractCyclicalScale(
                         mode=self._scalaStorage.getIntervalSequence())
        self.type = 'Scala: %s' % self._scalaStorage.fileName
        self.description = self._scalaStorage.description





class RagAsawari(ConcreteScale):
    '''A concrete pseudo-raga scale. 

    >>> from music21 import *
    >>> sc = scale.RagAsawari('c2') 
    >>> sc.pitches
    [C2, D2, F2, G2, A-2, C3]
    >>> sc.getPitches(direction='descending')
    [C3, B-2, A-2, G2, F2, E-2, D2, C2]
    '''

    def __init__(self, tonic=None):
        ConcreteScale.__init__(self, tonic=tonic)
        self._abstract = AbstractRagAsawari()
        self.type = 'Rag Asawari'



class RagMarwa(ConcreteScale):
    '''A concrete pseudo-raga scale. 

    >>> from music21 import *
    >>> sc = scale.RagMarwa('c2') 
    >>> # this gets a pitch beyond the terminus b/c of descending form max
    >>> sc.pitches
    [C2, D-2, E2, F#2, A2, B2, A2, C3, D-3]
    '''
#     >>> sc.getPitches(direction='descending')
#     [C2, D2, E2, G2, A2, C3]

    def __init__(self, tonic=None):
        ConcreteScale.__init__(self, tonic=tonic)
        self._abstract = AbstractRagMarwa()
        self.type = 'Rag Marwa'





class WeightedHexatonicBlues(ConcreteScale):
    '''A concrete scale based on a dynamic mixture of a minor pentatonic and the hexatonic blues scale.

    >>> from music21 import *
    '''

    def __init__(self, tonic=None):
        ConcreteScale.__init__(self, tonic=tonic)
        self._abstract = AbstractWeightedHexatonicBlues()
        self.type = 'Weighted Hexatonic Blues'








#-------------------------------------------------------------------------------
class Test(unittest.TestCase):
    
    def runTest(self):
        pass


    def testBasicLegacy(self):
        from music21 import note

        n1 = note.Note()
        
        CMajor = MajorScale(n1)
        
        assert CMajor.name == "C major"
        assert CMajor.getPitches()[6].step == "B"
        
#         CScale = CMajor.getConcreteMajorScale()
#         assert CScale[7].step == "C"
#         assert CScale[7].octave == 5
#         
#         CScale2 = CMajor.getAbstractMajorScale()
#         
#         for note1 in CScale2:
#             assert note1.octave == 0
#             #assert note1.duration.type == ""
#         assert [note1.name for note1 in CScale] == ["C", "D", "E", "F", "G", "A", "B", "C"]
        
        seventh = CMajor.pitchFromDegree(7)
        assert seventh.step == "B"
        
        dom = CMajor.getDominant()
        assert dom.step == "G"
        
        n2 = note.Note()
        n2.step = "A"
        
        aMinor = CMajor.getRelativeMinor()
        assert aMinor.name == "A minor", "Got a different name: " + aMinor.name
        
        notes = [note1.name for note1 in aMinor.getPitches()]
        self.assertEqual(notes, ["A", "B", "C", "D", "E", "F", "G", 'A'])
        
        n3 = note.Note()
        n3.name = "B-"
        n3.octave = 5
        
        bFlatMinor = MinorScale(n3)
        assert bFlatMinor.name == "B- minor", "Got a different name: " + bFlatMinor.name
        notes2 = [note1.name for note1 in bFlatMinor.getPitches()]
        self.assertEqual(notes2, ["B-", "C", "D-", "E-", "F", "G-", "A-", 'B-'])
        assert bFlatMinor.getPitches()[0] == n3.pitch
        assert bFlatMinor.getPitches()[6].octave == 6
        
#         harmonic = bFlatMinor.getConcreteHarmonicMinorScale()
#         niceHarmonic = [note1.name for note1 in harmonic]
#         assert niceHarmonic == ["B-", "C", "D-", "E-", "F", "G-", "A", "B-"]
#         
#         harmonic2 = bFlatMinor.getAbstractHarmonicMinorScale()
#         assert [note1.name for note1 in harmonic2] == niceHarmonic
#         for note1 in harmonic2:
#             assert note1.octave == 0
#             #assert note1.duration.type == ""
        
#         melodic = bFlatMinor.getConcreteMelodicMinorScale()
#         niceMelodic = [note1.name for note1 in melodic]
#         assert niceMelodic == ["B-", "C", "D-", "E-", "F", "G", "A", "B-", "A-", "G-", \
#                                "F", "E-", "D-", "C", "B-"]
        
#         melodic2 = bFlatMinor.getAbstractMelodicMinorScale()
#         assert [note1.name for note1 in melodic2] == niceMelodic
#         for note1 in melodic2:
#             assert note1.octave == 0
            #assert note1.duration.type == ""
        
        cNote = bFlatMinor.pitchFromDegree(2)
        assert cNote.name == "C"
        fNote = bFlatMinor.getDominant()
        assert fNote.name == "F"
        
        bFlatMajor = bFlatMinor.getParallelMajor()
        assert bFlatMajor.name == "B- major"
#         scale = [note1.name for note1 in bFlatMajor.getConcreteMajorScale()]
#         assert scale == ["B-", "C", "D", "E-", "F", "G", "A", "B-"]
        
        dFlatMajor = bFlatMinor.getRelativeMajor()
        assert dFlatMajor.name == "D- major"
        assert dFlatMajor.getTonic().name == "D-"
        assert dFlatMajor.getDominant().name == "A-"





    def testBasic(self):
        # deriving a scale from a Stream

        # just get default, c-major, as derive will check all tonics
        sc1 = MajorScale()
        sc2 = MinorScale()

        # we can get a range of pitches
        self.assertEqual(str(sc2.getPitches('c2', 'c5')), '[C2, D2, E-2, F2, G2, A-2, B-2, C3, D3, E-3, F3, G3, A-3, B-3, C4, D4, E-4, F4, G4, A-4, B-4, C5]')



        # we can transpose the Scale
        sc3 = sc2.transpose('-m3')
        self.assertEqual(str(sc3.getPitches('c2', 'c5')), '[C2, D2, E2, F2, G2, A2, B2, C3, D3, E3, F3, G3, A3, B3, C4, D4, E4, F4, G4, A4, B4, C5]')
        
        # getting pitches from scale degrees
        self.assertEqual(str(sc3.pitchFromDegree(3)), 'C4')
        self.assertEqual(str(sc3.pitchFromDegree(7)), 'G4')
        self.assertEqual(str(sc3.pitchesFromScaleDegrees([1,5,6])), '[A3, E4, F4, A4]')
        self.assertEqual(str(sc3.pitchesFromScaleDegrees([2,3], minPitch='c6', maxPitch='c9')), '[C6, B6, C7, B7, C8, B8, C9]')


        # given a pitch, get the scale degree
        sc4 = MajorScale('A-')
        self.assertEqual(sc4.getScaleDegreeFromPitch('a-'), 1)
        # default is name matching
        self.assertEqual(sc4.getScaleDegreeFromPitch('g#'), None)
        # can set pitchClass comparison attribute
        self.assertEqual(sc4.getScaleDegreeFromPitch('g#', 
            comparisonAttribute='pitchClass'), 1)
        self.assertEqual(sc4.getScaleDegreeFromPitch('e-', 
            comparisonAttribute='name'), 5)

        # showing scales
        # this assumes that the tonic is not the first scale degree
        sc1 = HypophrygianScale('c4')
        self.assertEqual(str(sc1.pitchFromDegree(1)), "G3")
        self.assertEqual(str(sc1.pitchFromDegree(4)), "C4")
        #sc1.show()

        sc1 = MajorScale()
        # deriving a new scale from the pitches found in a collection
        from music21 import corpus
        s = corpus.parse('bwv66.6')
        sc3 = sc1.derive(s.parts['soprano'])
        self.assertEqual(str(sc3), '<music21.scale.MajorScale A major>')

        sc3 = sc1.derive(s.parts['tenor'])
        self.assertEqual(str(sc3), '<music21.scale.MajorScale A major>')

        sc3 = sc2.derive(s.parts['bass'])
        self.assertEqual(str(sc3), '<music21.scale.MinorScale F# minor>')


        # composing with a scale
        from music21 import stream, note
        s = stream.Stream()
        p = 'd#4'
        #sc = PhrygianScale('e')
        sc = MajorScale('E4')
        for d, x in [('ascending', 1), ('descending', 2), ('ascending', 3), 
                    ('descending', 4), ('ascending', 3),  ('descending', 2), 
                    ('ascending', 1)]:
            # use duration type instead of quarter length
            for y in [1, .5, .5, .25, .25, .25, .25]:
                p = sc.next(p, direction=d, stepSize=x)
                n = note.Note(p)
                n.quarterLength = y
                s.append(n)
        self.assertEqual(str(s.pitches), '[E4, F#4, G#4, A4, B4, C#5, D#5, B4, G#4, E4, C#4, A3, F#3, D#3, G#3, C#4, F#4, B4, E5, A5, D#6, G#5, C#5, F#4, B3, E3, A2, D#2, G#2, C#3, F#3, B3, E4, A4, D#5, B4, G#4, E4, C#4, A3, F#3, D#3, E3, F#3, G#3, A3, B3, C#4, D#4]')
        #s.show()


        # composing with an octatonic scale.
        s1 = stream.Part()
        s2 = stream.Part()
        p1 = 'b4'
        p2 = 'b3'
        sc = OctatonicScale('C4')
        for d, x in [('ascending', 1), ('descending', 2), ('ascending', 3), 
                    ('descending', 2), ('ascending', 1)]:
            for y in [1, .5, .25, .25]:
                p1 = sc.next(p1, direction=d, stepSize=x)
                n = note.Note(p1)
                n.quarterLength = y
                s1.append(n)
            if d == 'ascending':
                d = 'descending'
            elif d == 'descending':
                d = 'ascending'
            for y in [1, .5, .25, .25]:
                p2 = sc.next(p2, direction=d, stepSize=x)
                n = note.Note(p2)
                n.quarterLength = y
                s2.append(n)
        s = stream.Score()
        s.insert(0, s1)
        s.insert(0, s2)
        #s.show()


        # compare two different major scales
        sc1 = MajorScale('g')
        sc2 = MajorScale('a')
        sc3 = MinorScale('f#')
        # exact comparisons
        self.assertEqual(sc1 == sc2, False)
        self.assertEqual(sc1.abstract == sc2.abstract, True)
        self.assertEqual(sc1 == sc3, False)
        self.assertEqual(sc1.abstract == sc3.abstract, False)

        # getting details on comparison
        self.assertEqual(str(sc1.match(sc2)), "{'notMatched': [C#5, G#5], 'matched': [A4, B4, D5, E5, F#5, A5]}")







    def testCyclicalScales(self):

        from music21 import scale

        sc = scale.CyclicalScale('c4', ['m2', 'm2']) 

        # we get speling based on maxAccidental paramete
        self.assertEqual(str(sc.getPitches('g4', 'g6')), '[G4, A-4, A4, B-4, C-5, C5, D-5, D5, E-5, F-5, F5, G-5, G5, A-5, A5, B-5, C-6, C6, D-6, D6, E-6, F-6, F6, G-6, G6]')

        # these values are different because scale degree 1 has different 
        # pitches in different registers, as this is a non-octave repeating
        # scale

        self.assertEqual(sc.abstract.getDegreeMaxUnique(), 2)

        self.assertEqual(str(sc.pitchFromDegree(1)), 'C4')
        self.assertEqual(str(sc.pitchFromDegree(1, 'c2', 'c3')), 'B#1')

        # scale storing parameters
        # how to get a spelling in different ways
        # ex: octatonic should always compare on pitchClass

        # a very short cyclical scale
        sc = scale.CyclicalScale('c4', 'p5') # can give one list
        self.assertEqual(str(sc.pitches), '[C4, G4]')

        self.assertEqual(str(sc.getPitches('g2', 'g6')), '[B-2, F3, C4, G4, D5, A5, E6]')

        
        # as single interval cycle, all are 1
        #environLocal.printDebug(['calling get scale degree from pitch'])
        self.assertEqual(sc.getScaleDegreeFromPitch('g4'), 1)
        self.assertEqual(sc.getScaleDegreeFromPitch('b-2', 
            direction=DIRECTION_ASCENDING), 1)

        



    def testDeriveByDegree(self):
        from music21 import scale

        sc1 = scale.MajorScale()
        self.assertEqual(str(sc1.deriveByDegree(7, 'G#')),
         '<music21.scale.MajorScale A major>')

        sc1 = scale.HarmonicMinorScale()
         # what scale has g# as its 7th degree
        self.assertEqual(str(sc1.deriveByDegree(7, 'G#')), 
        '<music21.scale.HarmonicMinorScale A harmonic minor>')
        self.assertEqual(str(sc1.deriveByDegree(2, 'E')), 
        '<music21.scale.HarmonicMinorScale D harmonic minor>')


        # add serial rows as scales


    def testMelodicMinorA(self):

        mm = MelodicMinorScale('a')
        self.assertEqual(str(mm.pitches), '[A4, B4, C5, D5, E5, F#5, G#5, A5]')

        self.assertEqual(str(mm.getPitches(direction='ascending')), '[A4, B4, C5, D5, E5, F#5, G#5, A5]')

        self.assertEqual(str(mm.getPitches('c1', 'c3', direction='descending')), '[C3, B2, A2, G2, F2, E2, D2, C2, B1, A1, G1, F1, E1, D1, C1]')


        # TODO: this shows a problem with a bidirectional scale: we are 
        # always starting at the tonic and moving up or down; so this is still
        # giving a descended portion, even though an asecnding portion was requested
        self.assertEqual(str(mm.getPitches('c1', 'c3', direction='ascending')), '[C1, D1, E1, F#1, G#1, A1, B1, C2, D2, E2, F#2, G#2, A2, B2, C3]')

        self.assertEqual(str(mm.getPitches('c1', 'c3', direction='descending')), '[C1, D1, E1, F1, G1, A1, B1, C2, D2, E2, F2, G2, A2, B2, C3]')


        self.assertEqual(str(mm.getPitches('a5', 'a6', direction='ascending')), '[A5, B5, C6, D6, E6, F#6, G#6, A6]')

        self.assertEqual(str(mm.getPitches('a5', 'a6', direction='descending')), '[A6, G6, F6, E6, D6, C6, B5, A5]')


        self.assertEqual(mm.getScaleDegreeFromPitch('a3'), 1)
        self.assertEqual(mm.getScaleDegreeFromPitch('b3'), 2)

        # ascending, by default, has 7th scale degree as g#
        self.assertEqual(mm.getScaleDegreeFromPitch('g#3'), 7)

        # in descending, G# is not present
        self.assertEqual(mm.getScaleDegreeFromPitch('g#3', direction='descending'), None)

        # but, g is
        self.assertEqual(mm.getScaleDegreeFromPitch('g3', direction='descending'), 7)

        # the bi directional representation has a version of each instance
        # merged
        self.assertEqual(str(mm.getPitches('a4', 'a5', direction='bi')), '[A4, B4, C5, D5, E5, F#5, F5, G#5, G5, A5]')

        # in a bi-directional representation, both g and g# are will return
        # scale degree 7
        self.assertEqual(mm.getScaleDegreeFromPitch('g8', direction='bi'), 7)
        self.assertEqual(mm.getScaleDegreeFromPitch('g#1', direction='bi'), 7)
        self.assertEqual(mm.getScaleDegreeFromPitch('f8', direction='bi'), 6)
        self.assertEqual(mm.getScaleDegreeFromPitch('f#1', direction='bi'), 6)


        self.assertEqual(mm.next('e5', 'ascending').nameWithOctave, 'F#5')
        #self.assertEqual(mm.next('f#5', 'ascending').nameWithOctave, 'F#5')

        self.assertEqual(mm.next('e5', 'descending').nameWithOctave, 'D5')

        self.assertEqual(mm.next('g#2', 'ascending').nameWithOctave, 'A2')
        #self.assertEqual(mm.next('g2', 'descending').nameWithOctave, 'f2')



    def testMelodicMinorB(self):
        '''Need to test descending form of getting pitches with no defined min and max
        '''
        mm = MelodicMinorScale('a')
#         self.assertEqual(str(mm.getPitches(None, None, direction='ascending')), '[A4, B4, C5, D5, E5, F#5, G#5, A5]')

        self.assertEqual(mm.pitchFromDegree(2, direction='ascending').nameWithOctave, 'B4')

        self.assertEqual(mm.pitchFromDegree(5, direction='ascending').nameWithOctave, 'E5')

        self.assertEqual(mm.pitchFromDegree(6, direction='ascending').nameWithOctave, 'F#5')

        self.assertEqual(mm.pitchFromDegree(6, direction='descending').nameWithOctave, 'F5')

        # todo: this is ambiguous case
        #self.assertEqual(mm.pitchFromDegree(6, direction='bi').nameWithOctave, 'F5')

        self.assertEqual(str(mm.getPitches(None, None, direction='descending')), '[A5, G5, F5, E5, D5, C5, B4, A4]')
        self.assertEqual(str(mm.getPitches(None, None, direction='ascending')), '[A4, B4, C5, D5, E5, F#5, G#5, A5]')



        self.assertEqual(str(mm.next('a3', 'ascending')), 'B3')

        self.assertEqual(str(mm.next('f#5', 'ascending')), 'G#5')
        self.assertEqual(str(mm.next('G#5', 'ascending')), 'A5')

        self.assertEqual(str(mm.next('f5', 'descending')), 'E5')
        self.assertEqual(str(mm.next('G5', 'descending')), 'F5')
        self.assertEqual(str(mm.next('A5', 'descending')), 'G5')


        self.assertEqual(str(mm.next('f#5', 'descending')), 'F5')
        self.assertEqual(str(mm.next('f#5', 'descending', 
            getNeighbor='descending')), 'E5')

        self.assertEqual(str(mm.next('f5', 'ascending')), 'F#5')
        self.assertEqual(str(mm.next('f5', 'ascending', 
            getNeighbor='descending')), 'F#5')



        # composing with a scale
        from music21 import stream, note
        s = stream.Stream()
        p = 'f#3'
        #sc = PhrygianScale('e')
        sc = MelodicMinorScale('g4')
        for direction in range(8):
            if direction % 2 == 0:
                d = 'ascending'
                qls = [1, .5, .5, 2, .25, .25, .25, .25]
            else:
                d = 'descending'                
                qls = [1, .5, 1, .5, .5]
            for y in qls:
                p = sc.next(p, direction=d, stepSize=1)
                n = note.Note(p)
                n.quarterLength = y
                s.append(n)
        s.makeAccidentals()

        self.assertEqual(str(s.pitches), '[G3, A3, B-3, C4, D4, E4, F#4, G4, F4, E-4, D4, C4, B-3, C4, D4, E4, F#4, G4, A4, B-4, C5, B-4, A4, G4, F4, E-4, E4, F#4, G4, A4, B-4, C5, D5, E5, E-5, D5, C5, B-4, A4, B-4, C5, D5, E5, F#5, G5, A5, B-5, A5, G5, F5, E-5, D5]')


        #s.show()



    def testPlot(self):

        try:
            import networkx
        except ImportError:
            networkx = None # use for testing

        if networkx is not None:
            amms = AbstractMelodicMinorScale()
            amms.plot(doneAction=None)


    def testPlagalModes(self):

        hs = HypophrygianScale('c4')
        self.assertEqual(str(hs.pitches), '[G3, A-3, B-3, C4, D-4, E-4, F4, G4]')

        self.assertEqual(str(hs.pitchFromDegree(1)), 'G3')



    def testRagAsawara(self):

        sc = RagAsawari('c4')
        self.assertEqual(str(sc.pitchFromDegree(1)), 'C4')

        #    
        # ascending should be:  [C2, D2, F2, G2, A-2, C3]

        self.assertEqual(str(sc.next('c4', 'ascending')), 'D4')
        self.assertEqual(str(sc.pitches), '[C4, D4, F4, G4, A-4, C5]')
# 
#         self.assertEqual(str(hs.pitchFromDegree(1)), 'G3')

        self.assertEqual(str(sc.getPitches('c2', 'c4', direction='ascending')), '[C2, D2, F2, G2, A-2, C3, D3, F3, G3, A-3, C4]')

        self.assertEqual(str(sc.getPitches('c2', 'c4', direction='descending')), '[C4, B-3, A-3, G3, F3, E-3, D3, C3, B-2, A-2, G2, F2, E-2, D2, C2]')

        self.assertEqual(str(sc.next('c1', 'ascending')), 'D1')
        self.assertEqual(str(sc.next('d1', 'ascending')), 'F1')
        self.assertEqual(str(sc.next('f1', 'descending')), 'E-1')

        self.assertEqual(str(sc.next('e-1', 'ascending', getNeighbor='descending')), 'F1')

        self.assertEqual(str(sc.pitchFromDegree(1)), 'C1')
        # there is no third step in ascending form
        self.assertEqual(str(sc.pitchFromDegree(3)), 'None')
        self.assertEqual(str(sc.pitchFromDegree(3, direction='descending')), 'E-4')

        self.assertEqual(str(sc.pitchFromDegree(7)), 'None')
        self.assertEqual(str(sc.pitchFromDegree(7, direction='descending')), 'B-4')





    def testRagMarwaA(self):

        sc = RagMarwa('c4')
        self.assertEqual(str(sc.pitchFromDegree(1)), 'C4')

        self.assertEqual(str(sc.next('c4', 'ascending')), 'D-4')

        self.assertEqual(str(sc.pitches), '[C4, D-4, E4, F#4, A4, B4, A4, C5, D-5]')

        self.assertEqual(str(sc.getPitches('c2', 'c3', direction='ascending')), '[C2, D-2, E2, F#2, A2, B2, A2, C3]')


        self.assertEqual(str(sc.getPitches('c2', 'c4', direction='ascending')), '[C2, D-2, E2, F#2, A2, B2, A2, C3, D-3, E3, F#3, A3, B3, A3, C4]')

        self.assertEqual(str(sc.getPitches('c3', 'd-4', direction='descending')), '[D-4, C4, D-4, B3, A3, F#3, E3, D-3, C3]')
 
        # is this correct: this cuts off the d-4, as it is outside of the range
        self.assertEqual(str(sc.getPitches('c3', 'c4', direction='descending')), '[C4, B3, A3, F#3, E3, D-3, C3]')
 

        self.assertEqual(str(sc.next('c1', 'ascending')), 'D-1')
        self.assertEqual(str(sc.next('d-1', 'ascending')), 'E1')
        self.assertEqual(str(sc.next('e1', 'ascending')), 'F#1')
        self.assertEqual(str(sc.next('f#1', 'ascending')), 'A1')
        # this is probabilistic
        #self.assertEqual(str(sc.next('A1', 'ascending')), 'B1')
        self.assertEqual(str(sc.next('B1', 'ascending')), 'A1')

        self.assertEqual(str(sc.next('B2', 'descending')), 'A2')
        self.assertEqual(str(sc.next('A2', 'descending')), 'F#2')
        self.assertEqual(str(sc.next('E2', 'descending')), 'D-2')
        # this is correct!
        self.assertEqual(str(sc.next('C2', 'descending')), 'D-2')
        self.assertEqual(str(sc.next('D-2', 'ascending')), 'E2')


    def testRagMarwaB(self):
        sc = RagMarwa('c4')

        # for rag marwa, and given only the pitch a, the scale can move to 
        # either b or c; this selection is determined by weighted random
        # selection.
        post = []
        for x in range(100):
            post.append(sc.getScaleDegreeFromPitch('A1', 'ascending'))
        self.assertEqual(post.count(5) > 30, True)
        self.assertEqual(post.count(7) > 30, True)


        # for rag marwa, and given only the pitch d-, the scale can move to 
        # either b or c; this selection is determined by weighted random
        # selection; can be 2 or 7
        post = []
        for x in range(100):
            post.append(sc.getScaleDegreeFromPitch('D-3', 'descending'))
        self.assertEqual(post.count(2) > 30, True)
        self.assertEqual(post.count(7) > 30, True)


    def testRagMarwaC(self):
        sc = RagMarwa('c4')

        self.assertEqual(sc.abstract._net.realizeTermini('c1', 'terminusLow'), (pitch.Pitch('C1'), pitch.Pitch('C2')))

        self.assertEqual(sc.abstract._net.realizeMinMax('c1', 'terminusLow'), (pitch.Pitch('C1'), pitch.Pitch('D-2')))

        # descending from d-2, we can either go to c2 or b1
        post = []
        for x in range(100):
            post.append(str(sc.next('D-2', 'descending')))
        self.assertEqual(post.count('C2') > 30, True)
        self.assertEqual(post.count('B1') > 30, True)


    def testWeightedHexatonicBluesA(self):

        sc = WeightedHexatonicBlues('c4')

        i = 0
        j = 0
        for x in range(50):
            # over 50 iterations, it must be one of these two options
            match = str(sc.getPitches('c3', 'c4'))
            if match == '[C3, E-3, F3, G3, B-3, C4]':
                i += 1
            if match == '[C3, E-3, F3, F#3, G3, B-3, C4]':
                j += 1
            self.assertEqual(match in [
            '[C3, E-3, F3, G3, B-3, C4]', 
            '[C3, E-3, F3, F#3, G3, B-3, C4]'], 
            True)
        # check that we got at least one; this may fail rarely
        self.assertEqual(i >= 1, True)
        self.assertEqual(j >= 1, True)
        

        # test descending
        i = 0
        j = 0
        for x in range(50):
            # over 50 iterations, it must be one of these two options
            match = str(sc.getPitches('c3', 'c4', direction='descending'))
            if match == '[C4, B-3, G3, F3, E-3, C3]':
                i += 1
            if match == '[C4, B-3, G3, F#3, F3, E-3, C3]':
                j += 1
            self.assertEqual(match in [
            '[C4, B-3, G3, F3, E-3, C3]', 
            '[C4, B-3, G3, F#3, F3, E-3, C3]'], 
            True)
        # check that we got at least one; this may fail rarely
        self.assertEqual(i >= 1, True)
        self.assertEqual(j >= 1, True)


        self.assertEqual(str(sc.pitchFromDegree(1)), 'C4')
        self.assertEqual(str(sc.next('c4', 'ascending')), 'E-4')
 

        # degree 4 is always the blues note in this model
        self.assertEqual(str(sc.pitchFromDegree(4)), 'F#4')

        # this should always work, regardless of what scale is 
        # realized
        for trial in range(30):
            self.assertEqual(str(sc.next('f#3', 'ascending')) in ['G3', 'F#3'], True)
            # presently this might return the same note, if the
            # F# is taken as out of the scale and then found back in the Scale
            # in generation
            self.assertEqual(str(sc.next('f#3', 'descending')) in ['F3', 'F#3'], True)



    def testNextA(self):

        sc = MajorScale('c4')

        # ascending works in pitch space
        self.assertEqual(str(sc.next('a4', 'ascending', 1)),  'B4')
        self.assertEqual(str(sc.next('b4', 'ascending', 1)),  'C5')
        self.assertEqual(str(sc.next('b5', 'ascending', 1)),  'C6')
        self.assertEqual(str(sc.next('b3', 'ascending', 1)),  'C4')

        # descending works in pitch space
        self.assertEqual(str(sc.next('c3', 'descending', 1)),  'B2')
        self.assertEqual(str(sc.next('c8', 'descending', 1)),  'B7')

        sc = MajorScale('a4')

        self.assertEqual(str(sc.next('g#2', 'ascending', 1)),  'A2')
        self.assertEqual(str(sc.next('g#4', 'ascending', 1)),  'A4')


    def testIntervalBetweenDegrees(self):

        sc = MajorScale('c4')
        self.assertEqual(str(sc.intervalBetweenDegrees(3,4)), '<music21.interval.Interval m2>')
        self.assertEqual(str(sc.intervalBetweenDegrees(1,7)), '<music21.interval.Interval M7>')
        self.assertEqual(str(sc.intervalBetweenDegrees(1,5)), '<music21.interval.Interval P5>')
        self.assertEqual(str(sc.intervalBetweenDegrees(2,4)), '<music21.interval.Interval m3>')

        # with a probabilistic non deterministci scale, 
        # an exception may be raised for step that may not exist
        sc = WeightedHexatonicBlues('g3')
        exceptCount = 0
        for x in range(10):
            post = None
            try:
                post = sc.intervalBetweenDegrees(3, 4)
            except ScaleException:
                exceptCount += 1
            if post is not None:
                self.assertEqual(str(post), '<music21.interval.Interval A1>')
        self.assertEqual(exceptCount < 3, True)


    def testScalaScaleA(self):

        msg = '''! fj-12tet.scl
!  
Franck Jedrzejewski continued fractions approx. of 12-tet 
 12
!  
89/84
55/49
44/37
63/50
4/3
99/70
442/295
27/17
37/22
98/55
15/8
2/1

'''
        # provide a raw scala string
        sc = ScalaScale('c4', msg)
        self.assertEqual(str(sc), '<music21.scale.ScalaScale C Scala: fj-12tet.scl>')
        self.assertEqual(str(sc.getPitches('c2', 'c4')), '[C2(+0c), C#2(+0c), C##2(0c), D#2(0c), E2(+0c), E#2(-2c), F#2(+0c), F##2(0c), G#2(+1c), A2(+0c), B-2(+0c), B2(-12c), C3(+0c), C#3(+0c), C##3(0c), D#3(0c), E3(+0c), E#3(-2c), F#3(+0c), F##3(0c), G#3(+1c), A3(+0c), B-3(+0c), B3(-12c), C4]')



    def testScalaScaleOutput(self):
        sc = MajorScale('c4')
        ss = sc.getScalaStorage()
        self.assertEqual(ss.pitchCount, 7)
        msg = '''!
<music21.scale.MajorScale C major>
7
!
200.0
400.0
500.0
700.0
900.0
1100.0
1200.0
'''
        self.assertEqual(ss.getFileString(), msg)
        

    def testScalaScaleB(self):
        # test importing from scala archive
        from music21 import scale, stream, meter, note

        sc = scale.ScalaScale('e2', 'fj 12tet')
        # this is showing that there are slight microtonal adjustments but they are less than one cent large
        self.assertEqual(str(sc.pitches), '[E2, F2(+0c), F#2(0c), G2(0c), A-2(+0c), G##2(-2c), B-2(+0c), B2(0c), C3(+1c), D-3(+0c), D3(+0c), D#3(-12c), E3]')

        # 7 tone scale
        sc = scale.ScalaScale('c2', 'mbira zimb')
        self.assertEqual(str(sc.pitches), '[C2, C#2(-2c), D~2(+21c), E~2(+22c), F#~2(-8c), G~2(+21c), A~2(+2c), B~2(-2c)]')

        # 21 tone scale
        sc = scale.ScalaScale('c2', 'mbira_mude')
        self.assertEqual(str(sc.pitches), '[C2, D`2(+24c), D#2(-11c), F#2(-25c), F#2(+12c), G~2(+20c), B~2(-4c), A#2(-24c), E#3(-22c), D~3(+17c), F#~3(-2c), G#3(-13c), A3(+15c), C#~3(-24c), A3(+17c), B~3(-2c), C#~4(-22c), D~4(-4c), E~4(+10c), F#~4(-18c), G#4(+5c), B`4(+15c)]')
        #sc.show()

        # two octave slendro scale
        sc = scale.ScalaScale('c2', 'slendro_pliat')
        self.assertEqual(str(sc.pitches), '[C2, D~2(-15c), E~2(+4c), G2(+5c), A~2(-23c), C3, D~3(-15c), E~3(+4c), G3(+5c), A~3(-23c)]')


        # 5 note slendro scale
        sc = scale.ScalaScale('c2', 'slendro_ang2')
        self.assertEqual(str(sc.pitches), '[C2, D#2(-22c), F~2(+19c), G~2(-10c), B`2(-8c), C3]')

        # 5 note slendro scale
        sc = scale.ScalaScale('c2', 'slendroc5.scl')
        self.assertEqual(str(sc.pitches), '[C2, D~2(-14c), E~2(+4c), G2(+5c), A~2(-22c), C3]')

        s = stream.Stream()
        s.append(meter.TimeSignature('6/4'))

        sc1 = scale.ScalaScale('c2', 'slendro_ang2')
        sc2 = scale.ScalaScale('c2', 'slendroc5.scl')
        p1 = stream.Part()
        p1.append([note.Note(p, lyric=p.microtone) for p in sc1.pitches])
        p2 = stream.Part()
        p2.append([note.Note(p, lyric=p.microtone) for p in sc2.pitches])
        s.insert(0, p1)
        s.insert(0, p2)
        #s.show()


    def testConcreteScaleA(self):
        # testing of arbitrary concrete scales
        from music21 import scale       
        sc = scale.ConcreteScale(pitches = ["C#3", "E-3", "F3", "G3", "B3", "D~4", "F#4", "A4", "C#5"])
        self.assertEqual(str(sc.getTonic()), 'C#3')
        
        self.assertEqual(sc.abstract.octaveDuplicating, False)
        
        self.assertEqual(str(sc.pitches), 
            '[C#3, E-3, F3, G3, B3, D~4, F#4, A4, C#5]')
        
        self.assertEqual(str(sc.getPitches('C#3', 'C#5')), 
            '[C#3, E-3, F3, G3, B3, D~4, F#4, A4, C#5]')
        
        self.assertEqual(str(sc.getPitches('C#1', 'C#5')), 
            '[C#1, E-1, F1, G1, B1, D~2, F#2, A2, C#3, E-3, F3, G3, B3, D~4, F#4, A4, C#5]')
        
        # a portio of the scale
        self.assertEqual(str(sc.getPitches('C#4', 'C#5')), 
            '[D~4, F#4, A4, C#5]')
        
        self.assertEqual(str(sc.getPitches('C#7', 'C#5')), 
            '[C#7, A6, F#6, D~6, B5, G5, F5, E-5, C#5]')
        
        
        sc = scale.ConcreteScale(pitches = ["C#3", "E-3", "F3", "G3", "B3", "C#4"])
        self.assertEqual(str(sc.getTonic()), 'C#3')
        self.assertEqual(sc.abstract.octaveDuplicating, True)



    def testTuneA(self):
        
        # fokker_12.scl  Fokker's 7-limit 12-tone just scale
        # pyth_12.scl                    12  12-tone Pythagorean scale
        from music21 import corpus, scale

        s = corpus.parse('bwv66.6')
        p1 = s.parts[0]
        #p1.show('midi')

        self.assertEqual(str(p1.pitches), '[C#5, B4, A4, B4, C#5, E5, C#5, B4, A4, C#5, A4, B4, G#4, F#4, A4, B4, B4, F#4, E4, A4, B4, C#5, C#5, A4, B4, C#5, A4, G#4, F#4, G#4, F#4, F#4, F#4, F#4, F#4, E#4, F#4]')

        sc = ScalaScale('C4', 'fokker_12.scl')
        self.assertEqual(str(sc.pitches), '[C4, D-4(+19c), D4(+4c), D~4(+17c), E4(-14c), F4(-2c), F#4(-10c), G4(+2c), A-4(+21c), G##4(-16c), A~4(+19c), B4(-12c), C5]')
        sc.tune(s)

        p1 = s.parts[0]
        # problem of not matching enhamronics
        self.assertEqual(str(p1.pitches), '[C#5(+19c), B4(-12c), A4(-16c), B4(-12c), C#5(+19c), E5(-14c), C#5(+19c), B4(-12c), A4(-16c), C#5(+19c), A4(-16c), B4(-12c), G#4(+21c), F#4(-10c), A4(-16c), B4(-12c), B4(-12c), F#4(-10c), E4(-14c), A4(-16c), B4(-12c), C#5(+19c), C#5(+19c), A4(-16c), B4(-12c), C#5(+19c), A4(-16c), G#4(+21c), F#4(-10c), G#4(+21c), F#4(-10c), F#4(-10c), F#4(-10c), F#4(-10c), F#4(-10c), E#4(-2c), F#4(-10c)]')
        #p1.show('midi')


    def testTuneB(self):
        
        # fokker_12.scl  Fokker's 7-limit 12-tone just scale
        # pyth_12.scl                    12  12-tone Pythagorean scale
        from music21 import corpus, scale

        s = corpus.parse('bwv66.6')
        sc = ScalaScale('C4', 'fokker_12.scl')
        self.assertEqual(str(sc.pitches), '[C4, D-4(+19c), D4(+4c), D~4(+17c), E4(-14c), F4(-2c), F#4(-10c), G4(+2c), A-4(+21c), G##4(-16c), A~4(+19c), B4(-12c), C5]')

        sc.tune(s)
        #s.show('midi')
        self.assertEqual(str(s.parts[0].pitches), '[C#5(+19c), B4(-12c), A4(-16c), B4(-12c), C#5(+19c), E5(-14c), C#5(+19c), B4(-12c), A4(-16c), C#5(+19c), A4(-16c), B4(-12c), G#4(+21c), F#4(-10c), A4(-16c), B4(-12c), B4(-12c), F#4(-10c), E4(-14c), A4(-16c), B4(-12c), C#5(+19c), C#5(+19c), A4(-16c), B4(-12c), C#5(+19c), A4(-16c), G#4(+21c), F#4(-10c), G#4(+21c), F#4(-10c), F#4(-10c), F#4(-10c), F#4(-10c), F#4(-10c), E#4(-2c), F#4(-10c)]')

        self.assertEqual(str(s.parts[1].pitches), '[E4(-14c), F#4(-10c), E4(-14c), E4(-14c), E4(-14c), E4(-14c), A4(-16c), G#4(+21c), E4(-14c), G#4(+21c), F#4(-10c), G#4(+21c), E#4(-2c), C#4(+19c), F#4(-10c), F#4(-10c), E4(-14c), D#4, C#4(+19c), C#4(+19c), F#4(-10c), E4(-14c), E4(-14c), A4(-16c), F#4(-10c), F#4(-10c), G#4(+21c), F#4(-10c), F#4(-10c), E#4(-2c), F#4(-10c), F#3(-10c), C#4(+19c), C#4(+19c), D4(+4c), E4(-14c), D4(+4c), C#4(+19c), B3(-12c), C#4(+19c), D4(+4c), C#4(+19c)]')

    def testTunePythag(self):
        '''
        Applies a pythagorean tuning to a section of D. Luca's Gloria
        and then uses Marchetto da Padova's very sharp #s and very flat
        flats (except B-flat) to inflect the accidentals
        '''
        
        from music21 import corpus, scale, instrument

        s = corpus.parse('luca/gloria').measures(70,79)
        for p in s:
            inst = p.flat.getElementsByClass(instrument.Instrument)[0]
            inst.midiProgram = 52
        sc = ScalaScale('F2', 'pyth_12.scl')
        sc.tune(s)
        for p in s.flat.pitches:
            if p.accidental is not None:
                if p.accidental.name == 'sharp':
                    p.microtone = p.microtone.cents + 45
                elif p.accidental.name == 'flat' and p.step == 'B':
                    p.microtone = p.microtone.cents - 20
                elif p.accidental.name == 'flat':
                    p.microtone = p.microtone.cents - 45
        #s.show()
        #s = s.transpose("P-4")
        #print s[0].measure(77).notes[1].microtone
        #s.show('midi')

#-------------------------------------------------------------------------------
# define presented order in documentation
_DOC_ORDER = [ConcreteScale, AbstractScale]


if __name__ == "__main__":
    # sys.arg test options will be used in mainTest()
    music21.mainTest(Test)

# store implicit tonic or Not
# if not set, then comparisons fall to abstract

#------------------------------------------------------------------------------
# eof




