# Service Source Code

This directory contains the application code for the CDK deployment.

## What are the preprocessing steps

1. [Video Collector](collection) is responsible for downloading YouTube videos into an Amazon S3 bucket
1. [OpenPose Analyzer](openposer) is responsible for annotating skeletal metadata from videos in S3 buckets
1. [Movement Extract](extract) is responsible for converting OpenPose skeletons into movement reports
1. [Movement Analyzer](analyze) is responsible for creating skeletal signatures
1. [Rekognition Overlay](rekon) is responsible for object detection within video frames

## What are the batch operation jobs

1. [Start Manifest File](start-manifest) passes an S3 inventory report to a given Amazon Lambda function

## What are the tools

1. [Publish Video Collection Tasks](tools/task_publisher/) pushes download tasks into an Amazon SQS queue.
1. [OpenPose Task Generator](tools/openpose_task_gen/) pushes analysis tasks into an Amazon SQS queue.
1. [Extract Manifest Generator](tools/extract_manifest_gen/) creates batch jobs for [Start Manifest File](start-manifest)
1. [Rekognition Manifest Generator](tools/rekon_manifest_gen/) creates an inventory report for [Start Manifest File](start-manifest)
