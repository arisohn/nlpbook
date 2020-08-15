import torch
from ratsnlp import nlpbook
from ratsnlp.nlpbook.classification import get_web_service_app
from transformers import AutoConfig, AutoTokenizer, AutoModelForSequenceClassification


if __name__ == "__main__":

    # 학습이 완료된 모델 준비
    args = nlpbook.DeployArguments(
        pretrained_model_cache_dir="/Users/david/works/cache/kcbert-base",
        downstream_model_checkpoint_path="/Users/david/works/cache/checkpoint/_ckpt_epoch_0.ckpt",
        downstream_task_name="document-classification",
        max_seq_length=128,
    )
    fine_tuned_model_ckpt = torch.load(
        args.downstream_model_checkpoint_path,
        map_location=torch.device("cpu")
    )
    # 계산 그래프를 학습 때처럼 그려놓고,
    pretrained_model_config = AutoConfig.from_pretrained(
        args.pretrained_model_cache_dir,
        num_labels=fine_tuned_model_ckpt['state_dict']['model.classifier.bias'].shape.numel(),
    )
    model = AutoModelForSequenceClassification.from_config(pretrained_model_config)
    # 학습된 모델의 체크포인트를 해당 그래프에 부어넣는다
    model.load_state_dict({k.replace("model.", ""): v for k, v in fine_tuned_model_ckpt['state_dict'].items()})
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(
        args.pretrained_model_cache_dir,
        do_lower_case=False,
    )

    def inference_fn(sentence):
        inputs = tokenizer(
            [sentence],
            max_length=args.max_seq_length,
            padding="max_length",
            truncation=True,
        )
        with torch.no_grad():
            logits, = model(**{k: torch.tensor(v) for k, v in inputs.items()})
            prob = logits.softmax(dim=1)
            positive_prob = round(prob[0][1].item(), 4)
            negative_prob = round(prob[0][0].item(), 4)
            pred = "긍정 (positive)" if torch.argmax(prob) == 1 else "부정 (negative)"
        return {
            'sentence': sentence,
            'prediction': pred,
            'positive_data': f"긍정 {positive_prob}",
            'negative_data': f"부정 {negative_prob}",
            'positive_width': f"{positive_prob * 100}%",
            'negative_width': f"{negative_prob * 100}%",
        }

    app = get_web_service_app(inference_fn)
    app.run(host='0.0.0.0', port=5000)
