@CLS
@ECHO OFF
@ECHO ==================================
@ECHO Deployment Tool
@ECHO Nate Bachmeier - 2022
@ECHO ==================================

@SETLOCAL enableextensions enabledelayedexpansion
@SET base_path=%~dp0
@PUSHD %base_path%

@CALL docker build -t collector .
@CALL docker run -it -v %userprofile%\.aws:/root/.aws --env-file=debug.env --entrypoint bash collector