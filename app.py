from __future__ import print_function
import json
import boto3
import logging
import time
import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info('################  Event: ############## ' + str(event))
    #print('Received event: ' + json.dumps(event, indent=2))

    ids = []

    try:
        region = event['region']
        detail = event['detail']
        eventname = detail['eventName']
        arn = detail['userIdentity']['arn']
        principal = detail['userIdentity']['principalId']
        userType = detail['userIdentity']['type']

        if userType == 'IAMUser':
            user = detail['userIdentity']['userName']

        else:
            user = principal.split(':')[1]


        logger.info('principalId: ' + str(principal))
        logger.info('region: ' + str(region))
        logger.info('eventName: ' + str(eventname))
        logger.info('detail: ' + str(detail))
        '''
        if not detail['responseElements']:
            logger.warning('No responseElements found')
            if detail['errorCode']:
                logger.error('errorCode: ' + detail['errorCode'])
            if detail['errorMessage']:
                logger.error('errorMessage: ' + detail['errorMessage'])
            return False
        '''
        ec2_client = boto3.resource('ec2')
        lambda_client = boto3.client('lambda')
        rds_client = boto3.client('rds')
        s3_client = boto3.resource('s3')
        ddb_client = boto3.client('dynamodb')

        if eventname == 'CreateVolume':
            ids.append(detail['responseElements']['volumeId'])
            logger.info(ids)

        elif eventname == 'RunInstances':
            items = detail['responseElements']['instancesSet']['items']
            for item in items:
                ids.append(item['instanceId'])
            logger.info(ids)
            logger.info('number of instances: ' + str(len(ids)))

            base = ec2_client.instances.filter(InstanceIds=ids)

            #loop through the instances
            for instance in base:
                for vol in instance.volumes.all():
                    ids.append(vol.id)
                for eni in instance.network_interfaces:
                    ids.append(eni.id)

        elif eventname == 'CreateImage':
            ids.append(detail['responseElements']['imageId'])
            logger.info(ids)

        elif eventname == 'CreateSnapshot':
            ids.append(detail['responseElements']['snapshotId'])
            logger.info(ids)
            
        elif eventname == 'CreateFunction20150331':
            try:
                functionArn = detail['responseElements']['functionArn']
                lambda_client.tag_resource(Resource=functionArn,Tags={'CreatorNetID': user})
            except:
                pass
        elif eventname == 'UpdateFunctionConfiguration20150331v2':
            try:
                functionArn = detail['responseElements']['functionArn']
                lambda_client.tag_resource(Resource=functionArn,Tags={'LastConfigModifiedByNetID': user})
            except:
                pass
        elif eventname == 'UpdateFunctionCode20150331v2':
            try:
                functionArn = detail['responseElements']['functionArn']
                lambda_client.tag_resource(Resource=functionArn,Tags={'LastCodeModifiedByNetID': user})
            except:
                pass
        elif eventname == 'CreateDBInstance':
            try:
                dbResourceArn = detail['responseElements']['dBInstanceArn']
                rds_client.add_tags_to_resource(ResourceName=dbResourceArn,Tags=[{'Key':'CreatorNetID','Value': user}])
            except:
                pass
        elif eventname == 'CreateBucket':
            try:
                bucket_name = detail['requestParameters']['bucketName']
                s3_client.BucketTagging(bucket_name).put(Tagging={'TagSet': [{'Key':'CreatorNetID','Value': user}]})
            except Exception as e:
                logger.error('Something went wrong: ' + str(e))
                pass
        elif eventname == 'CreateTable':
            try:
                tableArn = detail['responseElements']['tableDescription']['tableArn']
                ddb_client.tag_resource(ResourceArn=tableArn,Tags=[{'Key':'CreatorNetID','Value': user}])
            except:
                pass
        else:
            logger.warning('Not supported action')

        if ids:
            for resourceid in ids:
                print('Tagging resource ' + resourceid)
            ec2_client.create_tags(Resources=ids, Tags=[{'Key': 'CreatorNetID', 'Value': user}])

        logger.info(' Remaining time (ms): ' + str(context.get_remaining_time_in_millis()) + '\n')
        return True
    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return False