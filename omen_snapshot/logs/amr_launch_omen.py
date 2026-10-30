
import os,sys,json,subprocess,pathlib,runpy
root=pathlib.Path.home()/'bimanual-robot';os.chdir(root)
logs=pathlib.Path.home()/'AppData/Local/bimanual-robot/live-serving';logs.mkdir(parents=True,exist_ok=True)
if len(sys.argv)>1 and sys.argv[1]=='arms':
    import lerobot.motors,lerobot.rollout
    sys.path.insert(0,str(root/'tools/camera'))
    import resolve_camera_indices
    resolve_camera_indices.RIGHT_DEVPATH_HINT='2353db1a'
    models=pathlib.Path.home()/'lerobot-training/outputs'
    sys.argv=['rollout_service.py',f'--pour.policy={models}/water_pour_chassis_smolvla_80/checkpoints/016000/pretrained_model',f'--place.policy={models}/cup_place_chassis_smolvla_80/checkpoints/007000/pretrained_model','--stow.pose=place_end','--policy.device=cuda','--robot.type=bi_so_follower','--robot.id=arms','--robot.calibration_dir=calibration/bi_follower','--robot.left_arm_config.port=COM3','--robot.left_arm_config.gripper_protection=true','--robot.left_arm_config.disable_torque_on_disconnect=false','--robot.left_arm_config.max_relative_target=15','--robot.left_arm_config.cameras={ wrist: {type: opencv, index_or_path: {left}, width: 640, height: 480, fps: 30} }','--robot.right_arm_config.port=COM4','--robot.right_arm_config.disable_torque_on_disconnect=false','--robot.right_arm_config.max_relative_target=15','--robot.right_arm_config.cameras={ wrist: {type: opencv, index_or_path: {right}, width: 640, height: 480, fps: 30} }','--robot.cameras={ top: {type: opencv, index_or_path: {depth}, width: 640, height: 480, fps: 30, mirror: true} }']
    runpy.run_path(str(root/'tools/rollout/rollout_service.py'),run_name='__main__')
else:
    mode=sys.argv[1]
    if mode=='camera': args=[sys.executable,'-u',str(root/'tools/camera/astra_rgb_virtualcam_bridge.py'),'--send-pi','192.168.0.159:5600']
    elif mode=='launch-arms': args=[sys.executable,'-u',__file__,'arms']
    elif mode=='order': args=[sys.executable,'-u','-m','apps.service_order.service_order_server','--host','0.0.0.0','--port','8765','--backend','rollout-service','--auto-step-s','0.5','--state-dir',str(logs/'orders')]
    else: raise ValueError(mode)
    env=os.environ.copy();env['PYTHONIOENCODING']='utf-8'
    with (logs/(mode+'.log')).open('ab') as out:
        proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,cwd=root,env=env,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP,close_fds=True)
    (logs/(mode+'.pid')).write_text(str(proc.pid));print(json.dumps({'mode':mode,'pid':proc.pid,'log':str(logs/(mode+'.log'))}))

    proc.wait()
