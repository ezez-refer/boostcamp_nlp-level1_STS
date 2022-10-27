import wandb
from tqdm.auto import tqdm

import torch
import pytorch_lightning as pl

from data_loader.data_loaders import Dataloader
import model.model as module_arch

from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning.loggers import WandbLogger


def train(args):
    # dataloader와 model을 생성합니다.
    dataloader = Dataloader(args.model_name, args.batch_size, args.shuffle, args.train_path, args.dev_path,
                            args.test_path, args.predict_path)
    model = module_arch.RoBERTa_Base_Model(
        args.model_name, args.learning_rate)

    # wandb logger 설정
    wandb_logger = WandbLogger(project=args.project_name)
    # gpu가 없으면 'gpus=0'을, gpu가 여러개면 'gpus=4'처럼 사용하실 gpu의 개수를 입력해주세요
    trainer = pl.Trainer(
        gpus=1, max_epochs=args.max_epoch, logger=wandb_logger, log_every_n_steps=1)

    # Train part
    trainer.fit(model=model, datamodule=dataloader)
    trainer.test(model=model, datamodule=dataloader)

    # 학습이 완료된 모델을 저장합니다.
    torch.save(model, args.save_model)


def sweep(args):
    sweep_config = {
        'method': 'bayes',  # random: 임의의 값의 parameter 세트를 선택, #bayes : 베이지안 최적화
        'parameters': {
            'lr': {
                # parameter를 설정하는 기준을 선택합니다. uniform은 연속적으로 균등한 값들을 선택합니다.
                'distribution': 'uniform',
                'min': 1e-5,                 # 최소값을 설정합니다.
                'max': 1e-4                  # 최대값을 설정합니다.
            },
            'batch_size': {
                'values': [16, 32, 64]  # 배치 사이즈 조절
            }
        },
        # 위의 링크에 있던 예시
        'early_terminate': {
            'type': 'hyperband',
            'max_iter': 30,  # 프로그램에 대해 최대 반복 횟수 지정, min과 max는 같이 사용 불가능한듯
            's': 2
        }
    }

    # pearson 점수가 최대화가 되는 방향으로 학습을 진행합니다.
    sweep_config['metric'] = {'name': 'val_pearson', 'goal': 'maximize'}

    def sweep_train(config=None):
        wandb.init(config=config)
        config = wandb.config

        dataloader = Dataloader(args.model_name, args.batch_size, args.shuffle,
                                args.train_path, args.dev_path, args.test_path, args.predict_path)
        model = module_arch.Model(args.model_name, config.lr)
        # project 인자 부분 잘 모르겠습니다
        wandb_logger = WandbLogger(project=args.project_name)

        trainer = pl.Trainer(gpus=1, max_epochs=args.max_epoch,
                             logger=wandb_logger, log_every_n_steps=1)
        trainer.fit(model=model, datamodule=dataloader)
        trainer.test(model=model, datamodule=dataloader)

    sweep_id = wandb.sweep(
        sweep=sweep_config,             # config 딕셔너리를 추가합니다.
        project=args.project_name         # project의 이름을 추가합니다.
    )

    wandb.agent(
        sweep_id=sweep_id,
        function=sweep_train,
        count=3
    )
