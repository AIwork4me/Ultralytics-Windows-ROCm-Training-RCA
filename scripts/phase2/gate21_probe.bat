@echo on
REM Gate-21 probe: what does an activated (yolo_amd) shell actually execute?
call conda activate yolo_amd
echo CONDA_DEFAULT_ENV=%CONDA_DEFAULT_ENV%
echo CONDA_PREFIX=%CONDA_PREFIX%
echo PATH-beginning: %PATH:~0,400%
where python
where pip
where yolo
python -c "import sys,os; print(sys.executable); print(sys.prefix); print(sys.base_prefix); print(os.environ.get('CONDA_PREFIX'))"
python "%~dp0gate21_env_probe.py"
