#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

"""
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    https://bitbucket.org/MakeHuman/makehuman/

**Authors:**           Marc Flerackers

**Copyright(c):**      MakeHuman Team 2001-2017

**Licensing:**         AGPL3

    This file is part of MakeHuman (www.makehuman.org).

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.


Abstract
--------

TODO
"""

import math
import numpy as np
import guicommon
import module3d
import humanmodifier
import gui
import log
import getpath
from core import G
import guimodifier
import language

class MeasureTaskView(guimodifier.ModifierTaskView):

    def __init__(self, category, name, label=None, saveName=None, cameraView=None):
        super(MeasureTaskView, self).__init__(category, name, label, saveName, cameraView)

        self.ruler = Ruler(getpath.getSysDataPath('measurements/modeling_measurements.json'))
        self._createMeasureMesh()

        self.active_slider = None
        self.lastActive = None

        self.statsBox = self.addRightWidget(gui.GroupBox('Statistics'))
        self.height = self.statsBox.addWidget(gui.TextView('Height: '))
        self.chest = self.statsBox.addWidget(gui.TextView('Chest: '))
        self.waist = self.statsBox.addWidget(gui.TextView('Waist: '))
        self.hips = self.statsBox.addWidget(gui.TextView('Hips: '))

        '''
        self.braBox = self.addRightWidget(gui.GroupBox('Brassiere size'))
        self.eu = self.braBox.addWidget(gui.TextView('EU: '))
        self.jp = self.braBox.addWidget(gui.TextView('JP: '))
        self.us = self.braBox.addWidget(gui.TextView('US: '))
        self.uk = self.braBox.addWidget(gui.TextView('UK: '))
        '''

    def addSlider(self, sliderCategory, slider, enabledCondition):
        super(MeasureTaskView, self).addSlider(sliderCategory, slider, enabledCondition)

        slider.valueConverter = MeasurementValueConverter(self, slider.modifier)

        @slider.mhEvent
        def onBlur(event):
            slider = event
            self.onSliderBlur(slider)
        @slider.mhEvent
        def onFocus(event):
            slider = event
            self.onSliderFocus(slider)
        @slider.mhEvent
        def onChange(event):
            self.syncGUIStats()

    def _createMeasureMesh(self):
        self.measureMesh = module3d.Object3D('measure', 2)
        self.measureMesh.createFaceGroup('measure')

        count = max([len(vertIdx) for vertIdx in self.ruler.Measures.values()])

        self.measureMesh.setCoords(np.zeros((count, 3), dtype=np.float32))
        self.measureMesh.setUVs(np.zeros((1, 2), dtype=np.float32))
        self.measureMesh.setFaces(np.arange(count).reshape((-1,2)))

        self.measureMesh.setColor([255, 255, 255, 255])
        self.measureMesh.setPickable(0)
        self.measureMesh.updateIndexBuffer()
        self.measureMesh.priority = 50

        self.measureObject = self.addObject(guicommon.Object(self.measureMesh))
        self.measureObject.setShadeless(True)
        self.measureObject.setDepthless(True)

    def showGroup(self, name):
        self.groupBoxes[name].radio.setSelected(True)
        self.groupBox.showWidget(self.groupBoxes[name])
        self.groupBoxes[name].children[0].setFocus()

    def getMeasure(self, measure):
        human = G.app.selectedHuman
        measure = self.ruler.getMeasure(human, measure, G.app.getSetting('units'))
        return measure

    def hideAllBoxes(self):
        for box in self.groupBoxes.values():
            box.hide()

    def onShow(self, event):
        super(MeasureTaskView, self).onShow(event)

        if not self.lastActive:
            self.lastActive = self.groupBoxes['Neck'].children[0]
        self.lastActive.setFocus()

        self.syncGUIStats()
        self.updateMeshes()
        human = G.app.selectedHuman

    def onHide(self, event):
        human = G.app.selectedHuman

    def onSliderFocus(self, slider):
        self.lastActive = slider
        self.active_slider = slider
        self.updateMeshes()
        self.measureObject.show()

    def onSliderBlur(self, slider):
        self.lastActive = slider
        if self.active_slider is slider:
            self.active_slider = None
        self.measureObject.hide()

    def updateMeshes(self):
        if self.active_slider is None:
            return

        human = G.app.selectedHuman

        vertidx = self.ruler.Measures[self.active_slider.modifier.fullName]

        coords = human.meshData.coord[vertidx]
        self.measureMesh.coord[:len(vertidx),:] = coords
        self.measureMesh.coord[len(vertidx):,:] = coords[-1:]
        self.measureMesh.markCoords(coor = True)
        self.measureMesh.update()

    def onHumanChanged(self, event):
        if G.app.currentTask == self:
            self.updateMeshes()
            self.syncSliders()

    def onHumanTranslated(self, event):
        self.measureObject.setPosition(G.app.selectedHuman.getPosition())

    def onHumanRotated(self, event):
        self.measureObject.setRotation(G.app.selectedHuman.getRotation())

    def loadHandler(self, human, values, strict):
        pass

    def saveHandler(self, human, file):
        pass

    def syncGUIStats(self):
        self.syncStatistics()
        #self.syncBraSizes()

    def syncStatistics(self):
        human = G.app.selectedHuman

        height = human.getHeightCm()
        if G.app.getSetting('units') == 'metric':
            height = '%.2f cm' % height
        else:
            height = '%.2f in' % (height * 0.393700787)

        lang = language.language
        self.height.setTextFormat(lang.getLanguageString('Height') + ': %s', height)
        self.chest.setTextFormat(lang.getLanguageString('Chest') + ': %s', self.getMeasure('measure/measure-bust-circ-decr|incr'))
        self.waist.setTextFormat(lang.getLanguageString('Waist') + ': %s', self.getMeasure('measure/measure-waist-circ-decr|incr'))
        self.hips.setTextFormat(lang.getLanguageString('Hips') + ': %s', self.getMeasure('measure/measure-hips-circ-decr|incr'))

    def syncBraSizes(self):
        # TODO unused
        human = G.app.selectedHuman

        bust = self.ruler.getMeasure(human, 'measure/measure-bust-circ-decr|incr', 'metric')
        underbust = self.ruler.getMeasure(human, 'measure/measure-underbust-circ-decr|incr', 'metric')

        eucups = ['AA', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']

        mod = int(underbust)%5
        band = underbust - mod if mod < 2.5 else underbust - mod + 5
        cup = min(max(0, int(round(((bust - underbust - 10) / 2)))), len(eucups)-1)
        self.eu.setTextFormat('EU: %d%s', band, eucups[cup])

        jpcups = ['AAA', 'AA', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']

        mod = int(underbust)%5
        band = underbust - mod if mod < 2.5 else underbust - mod + 5
        cup = min(max(0, int(round(((bust - underbust - 5) / 2.5)))), len(jpcups)-1)
        self.jp.setTextFormat('JP: %d%s', band, jpcups[cup])

        uscups = ['AA', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']

        band = underbust * 0.393700787
        band = band + 5 if int(band)%2 else band + 4
        cup = min(max(0, int(round((bust - underbust - 10) / 2))), len(uscups)-1)
        self.us.setTextFormat('US: %d%s', band, uscups[cup])

        ukcups = ['AA', 'A', 'B', 'C', 'D', 'DD', 'E', 'F', 'FF', 'G', 'GG', 'H']

        self.uk.setTextFormat('UK: %d%s', band, ukcups[cup])


class MeasurementValueConverter(object):

    def __init__(self, task, modifier):
        self.task = task
        self.modifier = modifier
        self.value = 0.0

    @property
    def units(self):
        return 'cm' if G.app.getSetting('units') == 'metric' else 'in'

    @property
    def measure(self):
        # Measurements are linked to modifiers with the same name
        return self.modifier.fullName

    def dataToDisplay(self, value):
        """Perform measurement for specified modifier value."""
        self.value = value
        return self.task.getMeasure(self.measure)

    def displayToData(self, value):
        """Perform binary search to find modifier value that
        fits specified measurement value.
        """
        goal = float(value)
        measure = self.task.getMeasure(self.measure)
        minValue = -1.0
        maxValue = 1.0
        if math.fabs(measure - goal) < 0.01:
            return self.value
        else:
            tries = 10
            while tries:
                if math.fabs(measure - goal) < 0.01:
                    break;
                if goal < measure:
                    maxValue = self.value
                    if value == minValue:
                        break
                    self.value = minValue + (self.value - minValue) / 2.0
                    self.modifier.updateValue(self.value, 0)
                    measure = self.task.getMeasure(self.measure)
                else:
                    minValue = self.value
                    if value == maxValue:
                        break
                    self.value = self.value + (maxValue - self.value) / 2.0
                    self.modifier.updateValue(self.value, 0)
                    measure = self.task.getMeasure(self.measure)
                tries -= 1
        return self.value


class Ruler:
    """Ruler defines a set of rulers on the human from which measurements
    can be taken. Vertex indices on the basemesh are used as reference points.
    """

    def __init__(self, filename):
        """Create a set of measurement rulers from a measurement definition file."""
        self.Measures = {}
        self.fromFile(filename)

        self._validate()  # TODO this is only required if it is the intention to draw the rulers on the mesh, not a requirement per se for measuring

    def fromFile(self, filename):
        import json
        from collections import OrderedDict
        data = json.load(open(filename, 'rb'), object_pairs_hook=OrderedDict)
        for measurement_name, ruler_vertices in data.items():
            self.Measures[measurement_name] = ruler_vertices

    def _validate(self):
        """        
        Verify currectness of ruler specification
        """
        names = []
        for n,v in self.Measures.items():
            if len(v) % 2 != 0:
                names.append(n)
        if len(names) > 0:
            raise RuntimeError("One or more measurement rulers contain an uneven number of vertex indices. It's required that they are pairs indicating the begin and end point of every line to draw. Rulers with uneven index count: %s" % ", ".join(names))

    def getMeasure(self, human, measurementname, mode):
        measure_indices = self.Measures[measurementname]

        vecs = human.meshData.coord[measure_indices[:-1]] - human.meshData.coord[measure_indices[1:]]
        measures = np.sqrt(np.sum(vecs ** 2, axis=-1))[:,None]
        measure = np.sum(measures)

        if mode == 'metric':
            return 10.0 * measure
        else:
            return 10.0 * measure * 0.393700787

def load(app):
    """
    Plugin load function, needed by design.
    """
    category = app.getCategory('Modelling')

    humanmodifier.loadModifiers(getpath.getSysDataPath('modifiers/measurement_modifiers.json'), app.selectedHuman)
    guimodifier.loadModifierTaskViews(getpath.getSysDataPath('modifiers/measurement_sliders.json'), app.selectedHuman, category, taskviewClass=MeasureTaskView)


    # TODO ??
    #taskview.showGroup('neck')

def unload(app):
    pass

