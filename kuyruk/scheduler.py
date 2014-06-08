from kuyruk.process import KuyrukProcess
from kuyruk import importer
from setproctitle import setproctitle
from time import sleep
import logging
from datetime import datetime, timedelta
import shelve
import sys

logger = logging.getLogger(__name__)

class Scheduler(KuyrukProcess):

    """
    a basic scheduler, It kicks off tasks at regular intervals, which are then executed
    by the worker nodes available in the cluster.

    example config.

    SCHEDULE = {
        'runs-every-10-seconds':{
            'task': 'tasks.echo',
            'schedule': timedelta(seconds=10)
        },
        'runs-every-10-minutes':{
            'task': 'tasks.foo',
            'schedule': timedelta(minutes=10)
        }
    }

    SCHEDULER_FILE_NAME = '/home/users/ybrs/scheduler'

    """
    def __init__(self, kuyruk):
        super(Scheduler, self).__init__(kuyruk)

    def import_task(self, module, task):
        return importer.import_task(
            module, None, task, self.config.IMPORT_PATH)

    def get_last_run(self, k):
        return self.last_run.get(k, None)

    def fire_task(self, k, task, args):
        logging.info('sending due task - %s', task)
        task(*args)
        self.last_run[k] = datetime.utcnow()

    def warm_shutdown(self):
        sys.exit(0)

    def run(self):
        super(Scheduler, self).run()
        setproctitle("kuyruk: scheduler")
        self.schedule = {}
        self.last_run = shelve.open(self.config.SCHEDULER_FILE_NAME)

        for k, v in self.config.SCHEDULE.iteritems():
            try:
                # trying to get the defined task
                o = v['task'].split('.')
                module, task_name = '.'.join(o[:-1]), o[-1]
                task = self.import_task(module, task_name)
            except:
                logging.error('couldn\'t load task %s', v['task'])
                raise
            self.schedule[k] = {
                'task': task,
                'schedule': v['schedule'],
                'args': v.get('args', [])
            }
            logging.info("loaded task %s with schedule %s", task, v['schedule'])

        while True:
            for k, v in self.schedule.iteritems():
                last_run = self.get_last_run(k)
                logging.debug('last run of %s %s - %s', k, v['task'], last_run)
                if not last_run:
                    self.fire_task(k, v['task'], v['args'])
                else:
                    diff = datetime.utcnow() - last_run
                    if diff > v['schedule']:
                        self.fire_task(k, v['task'], v['args'])
            sleep(1)

if __name__ == "__main__":
    s = Scheduler()
    s.run()