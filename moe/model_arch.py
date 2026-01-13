import torch
import torch.nn as nn
from transformers import DistilBertModel


class StateFirstGatingModel(nn.Module):
    """
    狀態優先 (State-First) 混合神經網路架構
    特徵重組機制：壓縮語意特徵，擴張狀態特徵。
    """
    
    def __init__(self, n_classes: int, struct_dim: int = 7):
        super(StateFirstGatingModel, self).__init__()
        
        # 1. 語意流 (Semantic Stream)
        self.bert = DistilBertModel.from_pretrained('distilbert-base-multilingual-cased')
        
        # 文字瓶頸層 (Text Bottleneck)
        # 目的：將 768 維壓縮至 32 維，防止模型被使用者話術誤導
        self.text_compressor = nn.Sequential(
            nn.Linear(768, 32),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        
        # 2. 狀態流 (State Stream)
        # 狀態擴張層 (State Expansion)
        # 目的：將 7 維結構化特徵擴張至 128 維，使其成為決策主導力量
        self.struct_net = nn.Sequential(
            nn.Linear(struct_dim, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Dropout(0.1)
        )
        
        # 3. 決策層 (Gating Decision)
        # 輸入維度：32 (Text) + 128 (State) = 160
        self.classifier = nn.Sequential(
            nn.Linear(32 + 128, 64),
            nn.ReLU(),
            nn.Linear(64, n_classes) 
        )

    def forward(
        self, 
        input_ids: torch.Tensor, 
        attention_mask: torch.Tensor, 
        struct_features: torch.Tensor
    ):
        """
        前向傳播
        
        Args:
            input_ids: BERT input IDs
            attention_mask: BERT attention mask
            struct_features: 結構化特徵 (7 維)
        
        Returns:
            logits: 分類結果
        """
        # --- 處理文字特徵 ---
        bert_output = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        # 取 [CLS] token 代表整句語意
        pooled_output = bert_output.last_hidden_state[:, 0] 
        text_embed = self.text_compressor(pooled_output)  # Output: (batch, 32)
        
        # --- 處理結構化特徵 ---
        struct_embed = self.struct_net(struct_features)  # Output: (batch, 128)
        
        # --- 特徵融合與分類 ---
        combined = torch.cat((text_embed, struct_embed), dim=1)
        output = self.classifier(combined)
        
        return output
