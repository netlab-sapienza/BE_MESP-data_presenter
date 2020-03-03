from .utilities.singleton import Singleton
from .utilities.databaseManager import DatabaseManager
from .inputDAO import InputDAO
from .outputWriter import OutputWriter
from .utilities.logger import Logger



class Manipulator(metaclass=Singleton):
    def __init__(self):

        inputdao = InputDAO()
        ow = OutputWriter()

        subdirectories_list= inputdao.getSubdirectoriesList()

        for subdir in subdirectories_list:
            print('*** start subdir: ',subdir)
            lg = Logger()
            res = self.manageSubcase(subdir)
            if res[0] != 0:
                err_code = '1MAN'  # MAN stands for Manipulator
                err_mess = 'ERROR WHILE PROCESSING SUBDIR: ' + str(subdir)
                err_details = 'ErroDetails: ' + res[1]
                raise Exception(err_code, err_mess, err_details)

            #todo: MANAGE SUBCASE


    def manageSubcase(self,subdir):
        logger = Logger()
        inputdao = InputDAO()

        res = inputdao.getFilesInDirectory(subdir)

        if res[0] != 0:
            return res

        if len(res[1]) < 1:
            return 2,'Empty subdirectory'

        convergence_times_per_file_list = []
        num_sent_update_msg_per_file_list = []

        for db_file in res[1]:
            #todo manage result!!!
            res = self.__performDbOperations(db_file)

            #todo: now this code is unreachable, implement error management in __performDbOperations()
            if res[0] != 0:
                err_code = '6MAN'  # MAN stands for Manipulator
                err_mess = 'ERROR WHILE PARSING FILE'
                err_details = 'ErroDetails: ' + str(res[1])
                raise Exception(err_code, err_mess, err_details)


            if res[1]:
                logger.log('FileConvergence','file ' + db_file.split('/')[-1] + ' in ' + subdir.split('/')[-1]
                           + ' CONVERGES  with max_convergence_time: ' + str(res[2])
                           + ' and  total_number_sent_update_msg: ' + str(res[3]))

                convergence_times_per_file_list.append(res[2])
                num_sent_update_msg_per_file_list.append(res[3])

            else:
                logger.log('FileConvergence', 'file ' + db_file.split('/')[-1] + ' in ' + subdir.split('/')[-1]
                           + ' DOES NOT CONVERGE')


        if len(convergence_times_per_file_list) == 0:
            logger.log('SubcaseFailure', 'subdirectory ' + subdir.split('/')[-1]
                       + ' does not contain any convergent db file (run), DROPPED')
            return 0,False
        else:
            #todo compute mean and variance of both convergenze_times and sent advertisement packets

            return 0, True


#SELECT * FROM events JOIN typeEvent_message_sent ON events.event_id = typeEvent_message_sent.event_id WHERE( events.submitter_id='AAAAA' and events.type = 0 and typeEvent_message_sent.message_type=0)
    def __performDbOperations(self,db_file):
        print('***2 start db_file ',db_file)
        db_manager = DatabaseManager(db_file)


        res = db_manager.getUsersList()

        if res[0] != 0:
            err_code = '2MAN'  # MAN stands for Manipulator
            err_mess = 'ERROR WHILE getting UserList from DB: '
            err_details = 'ErroDetails: ' + res[1]
            raise Exception(err_code,err_mess,err_details)

        userList = res[1]
        print('USERLIST: ',userList)

        total_num_sent_update_msg = 0
        highest_convercence_times_list=[]

        for user in userList:
            res = db_manager.getSentMessageEvents(user,0)
            if res[0] != 0:
                err_code = '3MAN'  # MAN stands for Manipulator
                err_mess = 'ERROR WHILE getting Sent Message Events from DB: '
                err_details = 'ErrorDetails: ' + res[1]
                raise Exception(err_code, err_mess, err_details)

            user_sent_update_msg_list = res[1]
            total_num_sent_update_msg = total_num_sent_update_msg + len(user_sent_update_msg_list)

            convergence_times = []
            for msg in user_sent_update_msg_list:
                payload = msg[-1]
                res = self.__checkConvergenceMessage(userList,payload)

                if res[1]:
                    convergence_times.append(msg[2])

            res = db_manager.getReceivedMessageEvents(user, 0)
            if res[0] != 0:
                err_code = '4MAN'  # MAN stands for Manipulator
                err_mess = 'ERROR WHILE getting Received Message Events from DB: '
                err_details = 'ErrorDetails: ' + res[1]
                raise Exception(err_code, err_mess, err_details)

            user_rcv_update_msg_list = res[1]

            for msg in user_rcv_update_msg_list:
                payload = msg[-1]
                res = self.__checkConvergenceMessage(userList,payload)

                if res[1]:
                    #can throw exceptions
                    convergence_times.append(int(msg[2]))

            if len(convergence_times) == 0:
                return 0,False

            highest_convercence_times_list.append(max(convergence_times))

        res = db_manager.getEarliestDeviceUpEvent()

        if res[0] != 0:
            err_code = '5MAN'  # MAN stands for Manipulator
            err_mess = 'ERROR WHILE getting Earliest Device-up Event from DB: '
            err_details = 'ErrorDetails: ' + res[1]
            raise Exception(err_code, err_mess, err_details)

        earliest_device_up_timestamp = res[1][0][2]
        max_convergence_time = int(max(highest_convercence_times_list)) - int(earliest_device_up_timestamp)

        print('first device-up ts: ', res[1][0][2], ' - max convergence time: ', max(highest_convercence_times_list),
              ' - total_num_sent_update_msg: ', total_num_sent_update_msg, ' - max_convergence_time: ',max_convergence_time)

        return 0,True,max_convergence_time,total_num_sent_update_msg


    def __checkConvergenceMessage(self,userList,payload):

        pl_split = payload.split('-')
        uL = list(userList)

        for index, elem in enumerate(pl_split):

            if elem in uL:
                uL.remove(elem)
        if len(uL) == 0:
            return 0,True

        return 0,False