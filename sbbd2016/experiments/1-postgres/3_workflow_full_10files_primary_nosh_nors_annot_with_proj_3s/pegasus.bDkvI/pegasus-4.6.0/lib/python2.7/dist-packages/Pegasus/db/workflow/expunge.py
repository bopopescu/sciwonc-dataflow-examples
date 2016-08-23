__author__ = "Monte Goode"

import os
import time
import logging

from Pegasus.db.schema import *
from Pegasus.db.modules import SQLAlchemyInit
from Pegasus.netlogger import util

class Expunge(SQLAlchemyInit):
    """
    Utility class to expunge a workflow and the associated data from
    a stampede schema database in the case of running with the replay
    option or a similar situation.

    The wf_uuid that is passed into the constructor MUST be the
    "top-level" workflow the user wants to delete.  Which is to
    say if the wf_uuid is a the child of another workflow, then
    only the data associated with that workflow will be deleted.
    Any parent or sibling workflows will be left untouched.

    Usage::

     from Pegasus.db.workflow.expunge import Expunge

     connString = 'sqlite:///pegasusMontage.db'
     wf_uuid = '1249335e-7692-4751-8da2-efcbb5024429'
     e = Expunge(connString, wf_uuid)
     e.expunge()

    All children/grand-children/etc information and associated
    workflows will be removed.
    """
    def __init__(self, connString, wf_uuid):
        """
        Init object

        @type   connString: string
        @param  connString: SQLAlchemy connection string - REQUIRED
        @type   wf_uuid: string
        @param  wf_uuid: The wf_uuid string of the workflow to remove
                along with associated data from the database
        """
        self.log = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self._connString = connString
        self._wf_uuid = wf_uuid
        SQLAlchemyInit.__init__(self, connString)

    def expunge(self):
        """
        Invoke this to remove workflow/information from DB.
        """
        raise NotImplementedError("Please use the appropriate Expunge implementation")

class StampedeExpunge(Expunge):
    def expunge(self):

        self.log.info('Expunging %s from workflow database', self._wf_uuid)

        query = self.session.query(Workflow).filter(Workflow.wf_uuid == self._wf_uuid)
        try:
            wf = query.one()
        except orm.exc.NoResultFound, e:
            self.log.warn('No workflow found with wf_uuid %s - aborting expunge', self._wf_uuid)
            return

        self.session.delete(wf)

        self.log.info('Flushing top-level workflow: %s', wf.wf_uuid)
        i = time.time()
        self.session.flush()
        self.session.commit()
        self.log.info('Flush took: %f seconds', time.time() - i)

class DashboardExpunge(Expunge):
    def expunge(self):
        """
        Invoke this to remove workflow/information from DB.
        """
        self.log.info('Expunging %s from dashboard database', self._wf_uuid)

        query = self.session.query(DashboardWorkflow).filter(DashboardWorkflow.wf_uuid == self._wf_uuid)
        try:
            wf = query.one()
        except orm.exc.NoResultFound, e:
            self.log.warn('No workflow found with wf_uuid %s - aborting expunge', self._wf_uuid)
            return

        query = self.session.query(DashboardWorkflowstate).filter(DashboardWorkflowstate.wf_id == wf.wf_id)
        try:
            states = query.all()
        except orm.exc.NoResultFound, e:
            self.log.warn('No dashboard workflow state found with workflow found with wf_uuid %s - aborting expunge', self._wf_uuid)
            return

        # expunge all the associated workflow states first
        for state in states:
            self.log.info('Expunging workflow state for workflow : %s', wf.wf_id)
            self.session.delete(state)

        # expunge the workflow from the workflow table
        self.session.delete(wf)

        i = time.time()
        self.session.flush()
        self.session.commit()
        self.log.info('Flush took: %f seconds', time.time() - i)

