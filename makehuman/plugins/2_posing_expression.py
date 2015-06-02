#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

"""
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    https://bitbucket.org/MakeHuman/makehuman/

**Authors:**           Jonas Hauquier

**Copyright(c):**      MakeHuman Team 2001-2015

**Licensing:**         AGPL3 (http://www.makehuman.org/doc/node/the_makehuman_application.html)

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

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

Library for facial expression poses, these poses are set as rest pose and override
the orientation of the face bones of the human's base skeleton over the orientations
set by the (body) pose.
"""

import os
import json

import gui3d
import bvh
import getpath
import animation
import log
import filecache
import filechooser as fc


class ExpressionAction(gui3d.Action):
    def __init__(self, msg, before, filename, taskView):
        super(ExpressionAction, self).__init__(msg)
        self.filename = filename
        self.taskView = taskView
        self.before = before

    def do(self):
        self.taskView.chooseExpression(self.filename)
        return True

    def undo(self):
        self.taskView.chooseExpression(self.before)
        return True


class ExpressionTaskView(gui3d.TaskView, filecache.MetadataCacher):
    def __init__(self, category):
        gui3d.TaskView.__init__(self, category, 'Expressions')
        self.extension = 'mhupb'  # MH unit-pose blend (preliminary name)
        filecache.MetadataCacher.__init__(self, self.extension, 'expression_filecache.mhc')

        self.human = gui3d.app.selectedHuman
        self.selectedFile = None
        self.selectedPose = None
        self.face_bone_idxs = None

        self.base_bvh = None
        self.base_anim = None

        self._setting_pose = False

        self.sysDataPath = getpath.getSysDataPath('expressions')
        self.userPath = getpath.getDataPath('expressions')
        self.paths = [self.userPath, self.sysDataPath]
        if not os.path.exists(self.userPath):
            os.makedirs(self.userPath)

        self.filechooser = self.addRightWidget(fc.IconListFileChooser( \
                                                    self.paths,
                                                    self.extension,
                                                    'thumb',
                                                    name='Expression',
                                                    notFoundImage = getpath.getSysDataPath('notfound.thumb'),
                                                    noneItem = True,
                                                    doNotRecurse = True))
        self.filechooser.setIconSize(50,50)
        self.filechooser.enableAutoRefresh(False)

        @self.filechooser.mhEvent
        def onFileSelected(filename):
            if filename:
                msg = 'Load expression'
            else:
                msg = "Clear expression"
            gui3d.app.do(ExpressionAction(msg, self.selectedFile, filename, self))

        self.filechooser.setFileLoadHandler(fc.TaggedFileLoader(self))
        self.addLeftWidget(self.filechooser.createTagFilter())

    def _load_pose_units(self):
        from collections import OrderedDict
        self.base_bvh = bvh.load(getpath.getSysDataPath('poseunits/face-poseunits.bvh'), allowTranslation="none")
        self.base_anim = self.base_bvh.createAnimationTrack(self.human.getBaseSkeleton(), name="Expression-Face-PoseUnits")

        poseunit_json = json.load(open(getpath.getSysDataPath('poseunits/face-poseunits.json'),'rb'), object_pairs_hook=OrderedDict)
        self.poseunit_names = poseunit_json['framemapping']

        self.base_anim = animation.PoseUnit(self.base_anim.name, self.base_anim._data, self.poseunit_names)
        log.message('unit pose frame count:%s', len(self.poseunit_names))

        # Store indexes of all bones affected by face unit poses, should be all face bones
        self.face_bone_idxs = sorted(list(set([bIdx for l in self.base_anim.getAffectedBones() for bIdx in l])))

    def onShow(self, event):
        gui3d.TaskView.onShow(self, event)
        self.filechooser.refresh()
        self.filechooser.selectItem(self.selectedFile)

        if self.base_bvh is None:
            self._load_pose_units()

        if gui3d.app.getSetting('cameraAutoZoom'):
            gui3d.app.setFaceCamera()

    def _get_current_pose(self):
        if self.human.getActiveAnimation():
            return self.human.getActiveAnimation()
        else:
            return None

    def _get_current_unmodified_pose(self):
        pose = self._get_current_pose()
        if pose and hasattr(pose, 'pose_backref') and pose.pose_backref:
            return pose.pose_backref
        return pose

    def applyToPose(self, pose):
        if self.base_bvh is None:
            self._load_pose_units()
        self._setting_pose = True

        if self.human.getActiveAnimation() is None:
            # No pose set, simply set this one
            self.human.addAnimation(pose)
            self.human.setActiveAnimation(pose.name)
        else:
            # If the current pose was already modified by expression library, use the original one
            org_pose = self._get_current_unmodified_pose()
            pose_ = animation.mixPoses(org_pose, pose, self.face_bone_idxs)
            pose_.name = 'expr-lib-pose'
            pose_.pose_backref = org_pose
            self.human.addAnimation(pose_)
            self.human.setActiveAnimation('expr-lib-pose')

        self.human.setPosed(True)
        self.human.refreshPose()

        self._setting_pose = False

    def chooseExpression(self, filename):
        log.debug("Loading expression from %s", filename)
        self.selectedFile = filename

        if not filename:
            # Unload current expression
            self.selectedPose = None
            # Remove the expression from existing pose by restoring the original
            org_pose = self._get_current_unmodified_pose()
            if org_pose is None:
                self.human.setActiveAnimation(None)
            elif self.human.hasAnimation(org_pose.name):
                self.human.setActiveAnimation(org_pose.name)
            else:
                self.human.addAnimation(org_pose)
                self.human.setActiveAnimation(org_pose.name)

            # Remove pose reserved for expression library from human
            if self.human.hasAnimation('expr-lib-pose'):
                self.human.removeAnimation('expr-lib-pose')
            self.filechooser.selectItem(None)
            self.human.refreshPose(updateIfInRest=True)
            return

        # Assign to human
        self.selectedPose = animation.poseFromUnitPose('expr-lib-pose', filename, self.base_anim)
        self.applyToPose(self.selectedPose)
        self.human.refreshPose()

        self.filechooser.selectItem(filename)

    def getMetadataImpl(self, filename):
        import json
        mhupb = json.load(open(filename, 'rb'))
        name = mhupb['name']
        description = mhupb.get('description', '')
        tags = set([t.lower() for t in mhupb.get('tags', [])])
        return (tags, name, description)

    def getTagsFromMetadata(self, metadata):
        tags = metadata[0]
        return tags

    def getSearchPaths(self):
        return self.paths

    def onHumanChanging(self, event):
        pass

    def onHumanChanged(self, event):
        if self._setting_pose:
            return
        if event.change == 'poseChange':
            if self.selectedPose:
                self.applyToPose(self.selectedPose)

    def loadHandler(self, human, values, strict):
        # TODO make sure that this plugin loads values after pose plugin
        if values[0] == 'status':
            return

        if values[0] == 'expression' and len(values) > 1:
            if self.base_bvh is None:
                self._load_pose_units()

    def saveHandler(self, human, file):
        # TODO implement
        pass


# This method is called when the plugin is loaded into makehuman
# The app reference is passed so that a plugin can attach a new category, task, or other GUI elements

taskview = None
def load(app):
    global taskview
    category = app.getCategory('Pose/Animate')
    taskview = ExpressionTaskView(category)
    taskview.sortOrder = 4
    category.addTask(taskview)

    app.addLoadHandler('expression', taskview.loadHandler)
    app.addSaveHandler(taskview.saveHandler)


# This method is called when the plugin is unloaded from makehuman
# At the moment this is not used, but in the future it will remove the added GUI elements

def unload(app):
    taskview.onUnload()
