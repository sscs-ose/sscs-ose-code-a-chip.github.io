# 对称量化
# scale 通过 MSE 优化得到，没有求导

import torch
import torch.nn

import torch
import torch.nn as nn 
import numpy as np
from torch import Tensor
import torch.nn.functional as F



def find_best_scale(x_samples: torch.Tensor, nbits: int):
    """
    x_samples: shape [N, ...] 或 [N]，这里假定已flatten或可flatten。
    返回: (best_scale: torch.Tensor (scalar), min_err: float)
    """
    with torch.no_grad():
        x = x_samples.detach().flatten()
        qmin = -(2 ** (nbits - 1))
        qmax =  (2 ** (nbits - 1)) - 1

        # 初值：max-abs 对称量化
        x_abs_max = torch.max(torch.abs(x))
        eps = torch.finfo(x.dtype).eps if x.numel() > 0 else 1e-12
        s0 = torch.clamp(x_abs_max / max(qmax, 1), min=eps)

        def mse_for_scale(s):
            q = torch.clamp(torch.round(x / s), qmin, qmax)
            x_hat = q * s
            return torch.mean((x - x_hat) ** 2)

        # 粗网格（对数域）+ 局部细化
        candidates = [s0 * (10.0 ** p) for p in [-2, -1, -0.5, 0.0, 0.5, 1, 2]]
        errs = [mse_for_scale(s) for s in candidates]
        idx = int(torch.argmin(torch.stack(errs))) # torch.argmin 返回 坐标最小的索引
        best_s = candidates[idx]
        best_err = errs[idx]

        # 细化（可选）：在最佳的 ±(×sqrt(10)) 内再取几点
        refine = [best_s / (10 ** 0.5), best_s, best_s * (10 ** 0.5)]
        refine_errs = [mse_for_scale(s) for s in refine]
        ridx = int(torch.argmin(torch.stack(refine_errs)))
        best_s = refine[ridx]
        best_err = refine_errs[ridx]

        return torch.as_tensor(best_s, dtype=x.dtype, device=x.device), float(best_err)


# JL 在 PyTorch 中，继承 torch.autograd.Function 可以自定义前向传播和反向传播的行为
# 在 Float_to_Fix_STE 中，forward 和 backward 方法都被声明为静态方法，意味着它们不依赖于具体的类实例。
# 这与 PyTorch 自定义自动求导函数的设计有关：所有必要的信息都通过参数和 ctx（上下文对象）传递，而不需要通过实例变量存储数据。
class Float_to_Fix_STE(torch.autograd.Function):
    """
    Symmetric quantization with STE.
    Args:
        input:   fp tensor
        nbits:   int
        scale:   >0, can be scalar or per-channel (broadcastable to input)
        approx:  'round' | 'floor'
        verbose: bool
    """
    @staticmethod
    def forward(ctx, input, nbits, scale, approx='round', verbose=False):
        # 对称整数域（two's complement）
        qmin = -(2 ** (nbits - 1))
        qmax =  (2 ** (nbits - 1)) - 1

        # 检查 / 变形以便广播
        if torch.is_tensor(scale):
            assert (scale > 0).all(), "scale must be > 0"
            if scale.dim() > 0:
                # 约定：per-channel 放在 dim=0，向后广播到 input 的其余维度
                # [C, 1, 1] for 2D conv weight example
                scale = scale.view([scale.shape[0]] + [1] * (input.dim() - 1))
        else:
            assert scale > 0, "scale must be > 0"

        scaled = input / scale
        scaled = torch.clamp(scaled, qmin, qmax)

        if approx == 'floor':
            q = torch.floor(scaled)
        elif approx == 'round':
            q = torch.round(scaled)
        else:
            raise ValueError(f"Unknown approximation method: {approx}")

        out = q * scale
        if verbose:
            return out, q
        return out

    @staticmethod
    def backward(ctx, grad_output):
        # Straight-Through Estimator
        return grad_output, None, None, None, None

# backward 的返回值数量必须和 forward 的输入参数一致
# 由于这些参数在前向传播时充当的是超参数或者非可微分的常量，它们不需要也不应该计算梯度，因此返回 None。




class Uniform_Quantizer_with_Collecter(nn.Module):
    """
    A general-purpose uniform quantization + collector module 
    (does not distinguish sequence length, no per-step updates).

    - Uses find_best_scale(x_samples, nbits) to estimate the optimal scale (MSE), offline or online.
    - Quantization core: Float_to_Fix_STE.apply(input, nbits, scale, approx={'round'|'floor'}, verbose=False).
    - mode:
        'weight' -> scale is updated on every forward call (online calibration for weights).
        others   -> scale isn't auto-updated; call forward(..., collect=True) first then update().
    - fix_scale: if provided, always used (highest priority).
    - approx: 'round' or 'floor'.
    - verbose: if True, forward returns (y, y_int); otherwise returns y.
    """
    def __init__(self, nbits: int = 8, mode: str = 'value',
                 fix_scale: float | torch.Tensor | None = None,
                 name: str | None = None,
                 approx: str = 'round',
                 verbose: bool = False):
        super().__init__()
        self.nbits = nbits
        self.collector = None
        self.scale = None
        self.quantizer = Float_to_Fix_STE.apply
        self.update_at_call = (mode == 'weight')
        self.fix_scale = fix_scale
        self.name = name
        self.approx = approx
        self.verbose = verbose

    def forward(self, x: torch.Tensor, *, collect: bool = False):
        # 'weight'：每次用当前 x 估计并量化（除非 fix_scale 已给）
        if self.update_at_call:
            self.collector = x.detach()
            min_err = self.update()  # 刷新 self.scale
            if self.verbose:
                y, y_int = self.quantizer(x, self.nbits, self.scale, self.approx, True)
            else:
                y = self.quantizer(x, self.nbits, self.scale, self.approx, False)
            if min_err is not None and self.verbose:
                print(f'[Quantizer:{self.name}] MSE={float(min_err):.6e} | ||W_q||={float((y**2).mean().sqrt()):.6e}')
            return (y, y_int) if self.verbose else y

        # 非 'weight'：未校准前直通；有 scale 后才量化
        if self.scale is None:
            y = x
        else:
            if self.verbose:
                y, y_int = self.quantizer(x, self.nbits, self.scale, self.approx, True)
            else:
                y = self.quantizer(x, self.nbits, self.scale, self.approx, False)

        # 仅非 'weight' 模式下收集
        if not self.update_at_call and collect:
            x_flat = x.detach().flatten().unsqueeze(0)  # [1, N]
            self.collector = x_flat if self.collector is None else torch.cat([self.collector, x_flat], dim=0)

        return (y, y_int) if (self.verbose and self.scale is not None) else y

    @torch.no_grad()
    def update(self):
        # 优先使用固定 scale
        if self.fix_scale is not None:
            if torch.is_tensor(self.fix_scale):
                self.scale = self.fix_scale.to(dtype=self._infer_dtype(), device=self._infer_device())
            else:
                self.scale = torch.tensor(float(self.fix_scale), dtype=self._infer_dtype(), device=self._infer_device())
            self.collector = None
            return None

        if self.collector is None or self.collector.numel() == 0:
            return None

        best_s, min_err = find_best_scale(self.collector, self.nbits)
        self.scale = best_s.to(dtype=self._infer_dtype(), device=self._infer_device())
        self.collector = None
        return min_err

    def get_extra_state(self):
        return {'scale': self.scale}

    def set_extra_state(self, state):
        self.scale = state.get('scale', None)
        return state

    def reset_collector(self):
        self.collector = None

    def _infer_device(self):
        if isinstance(self.scale, torch.Tensor):
            return self.scale.device
        if isinstance(self.collector, torch.Tensor):
            return self.collector.device
        return torch.device('cpu')

    def _infer_dtype(self):
        if isinstance(self.scale, torch.Tensor):
            return self.scale.dtype
        if isinstance(self.collector, torch.Tensor):
            return self.collector.dtype
        return torch.float32





# conv groups 要求 Cin mod G=0,Cout mod G=0
# 输入通道被均匀分成 G 组，每组有 Cin/G 个通道。
# 输出通道也被均匀分成 G 组，每组有 Cout/G 个通道。
# 第 g 组输出通道 只和 第 g 组输入通道 相连。
# 不同组之间完全隔离，没有跨组连接。

# 空洞卷积 (dilation>1)
# 在卷积核元素之间插入“空格”，跳着取输入。
# dilation = d 表示：
# 核中相邻元素之间，隔着 d−1 个输入点。
# 卷积核大小不变，但 感受野 (receptive field) 扩大了。

# 权重不在自动更新scale，否则太慢了
class QuantConv2d(nn.Module):
    """
    Quantized Conv2d (drop-in) using your quantizers.

    - Weights:
        * nbits_weight, symmetric uniform quantization.
        * 'per_tensor' or 'per_channel' (per out-channel) scaling.
        * Still supports fixed scales via set_weight_fix_scale().

    - Activations:
        * Optional input/output activation quantization with nbits_act.
        * Activation scales follow collect -> update -> quantize.

    """

    _FLOAT_MODULE = nn.Conv2d

    def __init__(self,
                 in_channels: int,
                 out_channels: int,
                 kernel_size,
                 stride=1,
                 padding=0,
                 dilation=1,
                 groups=1,
                 bias=True,
                 *,
                 nbits_weight: int = 8,
                 nbits_act: int | None = 8,
                 weight_scale_mode: str = 'per_channel',   # 'per_tensor' | 'per_channel'
                 quantize_input: bool = True,
                 quantize_output: bool = False,
                 approx_w: str = 'round',
                 approx_a: str = 'round',
                 weight_fix_scale: float | torch.Tensor | None = None,
                 bias_fix_scale:   float | torch.Tensor | None = None,
                 device=None, dtype=None):
        super().__init__()
        factory_kwargs = {'device': device, 'dtype': dtype}

        kH, kW = kernel_size if isinstance(kernel_size, (tuple, list)) else (kernel_size, kernel_size)
        self.weight = nn.Parameter(torch.empty(out_channels, in_channels // groups, kH, kW, **factory_kwargs))
        self.bias   = nn.Parameter(torch.zeros(out_channels, **factory_kwargs)) if bias else None

        nn.init.kaiming_uniform_(self.weight, a=5 ** 0.5)
        if self.bias is not None:
            fan_in = in_channels * kH * kW
            bound = 1.0 / (fan_in ** 0.5)
            nn.init.uniform_(self.bias, -bound, bound)

        # Conv hyper-params
        self.stride   = stride
        self.padding  = padding
        self.dilation = dilation
        self.groups   = groups

        # Quant params
        assert weight_scale_mode in ('per_tensor', 'per_channel')
        self.weight_scale_mode = weight_scale_mode
        self.nbits_weight = nbits_weight
        self.nbits_act    = nbits_act
        self.approx_w     = approx_w
        self.approx_a     = approx_a
        self.quantize_input  = quantize_input and (nbits_act is not None)
        self.quantize_output = quantize_output and (nbits_act is not None)

        # ---- Weights/Bias quantizers (NO auto-update in forward) ----
        if self.weight_scale_mode == 'per_tensor':
            # NOTE: mode='value' => no auto scale search; forward is passthrough until Wupdate()/fix_scale
            self.w_quant = Uniform_Quantizer_with_Collecter(
                nbits=nbits_weight, mode='value', name='conv.weight', approx=self.approx_w, verbose=False,
                fix_scale=weight_fix_scale
            )
            self.b_quant = (Uniform_Quantizer_with_Collecter(
                nbits=nbits_weight, mode='value', name='conv.bias', approx=self.approx_w, verbose=False,
                fix_scale=bias_fix_scale
            ) if bias else None)

            self.w_quants = None
            self.b_quants = None
        else:
            # per-channel: one quantizer per out-channel
            self.w_quant = None
            self.b_quant = None
            self.w_quants = nn.ModuleList([
                Uniform_Quantizer_with_Collecter(
                    nbits=nbits_weight, mode='value', name=f'conv.weight[{c}]', approx=self.approx_w, verbose=False,
                    fix_scale=(weight_fix_scale[c] if (torch.is_tensor(weight_fix_scale)
                                                       and weight_fix_scale.dim()==1
                                                       and weight_fix_scale.numel()==out_channels)
                              else weight_fix_scale)
                ) for c in range(out_channels)
            ])
            self.b_quants = (nn.ModuleList([
                Uniform_Quantizer_with_Collecter(
                    nbits=nbits_weight, mode='value', name=f'conv.bias[{c}]', approx=self.approx_w, verbose=False,
                    fix_scale=(bias_fix_scale[c] if (torch.is_tensor(bias_fix_scale)
                                                    and bias_fix_scale.dim()==1
                                                    and bias_fix_scale.numel()==out_channels)
                              else bias_fix_scale)
                ) for c in range(out_channels)
            ]) if bias else None)

        # ---- Activations (collect -> update -> quantize) ----
        self.act_in_quant  = (Uniform_Quantizer_with_Collecter(
            nbits=nbits_act, mode='value', name='conv.act_in', approx=self.approx_a, verbose=False
        ) if self.quantize_input else None)

        self.act_out_quant = (Uniform_Quantizer_with_Collecter(
            nbits=nbits_act, mode='value', name='conv.act_out', approx=self.approx_a, verbose=False
        ) if self.quantize_output else None)

    # ---------- Weight quant ----------
    def _quantize_weight(self):
        W = self.weight
        if self.weight_scale_mode == 'per_tensor':
            return self.w_quant(W)  # passthrough until scale present
        # per-channel
        C = W.shape[0]
        Wq_slices = []
        for c in range(C):
            Wq_c = self.w_quants[c](W[c])  # passthrough until scale present
            Wq_slices.append(Wq_c)
        return torch.stack(Wq_slices, dim=0)

    # ---------- Bias quant ----------
    def _quantize_bias(self):
        if self.bias is None:
            return None
        if self.weight_scale_mode == 'per_tensor':
            return self.b_quant(self.bias) if self.b_quant is not None else self.bias
        # per-channel bias
        if self.b_quants is None:
            return self.bias
        bq_list = []
        for c in range(self.bias.numel()):
            bq_c = self.b_quants[c](self.bias[c])
            bq_list.append(bq_c)
        return torch.stack(bq_list, dim=0)

    # ---------- Forward ----------
    def forward(self, x: torch.Tensor, *, collect: bool = False):
        # input activation quant (collect-only until update())
        if self.act_in_quant is not None:
            x = self.act_in_quant(x, collect=collect)

        Wq = self._quantize_weight()
        bq = self._quantize_bias()

        y = F.conv2d(x, Wq, bq, self.stride, self.padding, self.dilation, self.groups)

        if self.act_out_quant is not None:
            y = self.act_out_quant(y, collect=collect)

        return y

    # ---------- Calibration / Update ----------
    @torch.no_grad()
    def act_collect(self, x: torch.Tensor, *, on_input: bool = True, on_output: bool = False):
        """Collect activation stats only (does not force quantization yet)."""
        xt = x
        if on_input and self.act_in_quant is not None:
            _ = self.act_in_quant(xt, collect=True)

        Wq = self._quantize_weight()
        bq = self._quantize_bias()
        y  = F.conv2d(xt, Wq, bq, self.stride, self.padding, self.dilation, self.groups)

        if on_output and self.act_out_quant is not None:
            _ = self.act_out_quant(y, collect=True)
        return y

    @torch.no_grad()
    def Wupdate(self):
        """
        One-shot calibration for weights/bias from current parameters.
        If fix_scale is set, quantizers will honor it and skip MSE search.
        """
        # Weights
        if self.weight_scale_mode == 'per_tensor':
            if self.w_quant is not None:
                self.w_quant.collector = self.weight.detach()
                self.w_quant.update()
        else:
            for c, q in enumerate(self.w_quants):
                q.collector = self.weight[c].detach()
                q.update()

        # Bias
        if self.bias is not None:
            if self.weight_scale_mode == 'per_tensor':
                if self.b_quant is not None:
                    self.b_quant.collector = self.bias.detach()
                    self.b_quant.update()
            else:
                if self.b_quants is not None:
                    for c, q in enumerate(self.b_quants):
                        q.collector = self.bias[c].detach()
                        q.update()

    @torch.no_grad()
    def Qupdate(self, mode: str = 'both'):
        """
        'activation': update act quantizers
        'weight':     update weight/bias quantizers from current params (no collecting needed)
        'both':       do both
        """
        if mode in ['both', 'activation']:
            if self.act_in_quant  is not None: self.act_in_quant.update()
            if self.act_out_quant is not None: self.act_out_quant.update()
        if mode in ['both', 'weight']:
            self.Wupdate()

    def act_update(self):
        return self.Qupdate(mode='activation')

    def reset_collector(self):
        if self.act_in_quant  is not None: self.act_in_quant.reset_collector()
        if self.act_out_quant is not None: self.act_out_quant.reset_collector()

    # ---------- Fix/clear scales after construction ----------
    def set_weight_fix_scale(self, s: float | torch.Tensor, *, for_bias: bool = False):
        if for_bias:
            if self.bias is None: return
            if self.weight_scale_mode == 'per_tensor':
                if self.b_quant is not None: self.b_quant.fix_scale = s
            else:
                if self.b_quants is None: return
                if torch.is_tensor(s) and s.dim()==1 and s.numel()==self.bias.numel():
                    for c, q in enumerate(self.b_quants): q.fix_scale = s[c]
                else:
                    for q in self.b_quants: q.fix_scale = s
            return

        if self.weight_scale_mode == 'per_tensor':
            self.w_quant.fix_scale = s
        else:
            C = self.weight.shape[0]
            if torch.is_tensor(s) and s.dim()==1 and s.numel()==C:
                for c, q in enumerate(self.w_quants): q.fix_scale = s[c]
            else:
                for q in self.w_quants: q.fix_scale = s

    def clear_weight_fix_scale(self, *, for_bias: bool = False):
        if for_bias:
            if self.weight_scale_mode == 'per_tensor':
                if self.b_quant is not None: self.b_quant.fix_scale = None
            else:
                if self.b_quants is not None:
                    for q in self.b_quants: q.fix_scale = None
            return

        if self.weight_scale_mode == 'per_tensor':
            self.w_quant.fix_scale = None
        else:
            for q in self.w_quants: q.fix_scale = None

    # ---------- Export ----------
    def export_weight_qparams(self):
        state = {'w_scale': None, 'b_scale': None, 'nbits_weight': self.nbits_weight, 'mode': self.weight_scale_mode}
        if self.weight_scale_mode == 'per_tensor':
            if hasattr(self.w_quant, 'scale') and self.w_quant.scale is not None:
                state['w_scale'] = self.w_quant.scale.detach().clone()
            if self.bias is not None and self.b_quant is not None and self.b_quant.scale is not None:
                state['b_scale'] = self.b_quant.scale.detach().clone()
        else:
            w_scales = [q.scale for q in self.w_quants]
            if all(s is not None for s in w_scales):
                state['w_scale'] = torch.stack([s.detach().clone() for s in w_scales], dim=0)
            if self.bias is not None and self.b_quants is not None:
                b_scales = [q.scale for q in self.b_quants]
                if all(s is not None for s in b_scales):
                    state['b_scale'] = torch.stack([s.detach().clone() for s in b_scales], dim=0)
        return state

    def export_act_qparams(self):
        return {
            'act_in_scale' : (self.act_in_quant.scale.detach().clone()
                              if (self.act_in_quant is not None and self.act_in_quant.scale is not None) else None),
            'act_out_scale': (self.act_out_quant.scale.detach().clone()
                              if (self.act_out_quant is not None and self.act_out_quant.scale is not None) else None),
            'nbits_act': self.nbits_act
        }


class QuantLinear(nn.Module):
    """Quantized Linear layer built with the same quantizer blocks as QuantConv2d."""

    _FLOAT_MODULE = nn.Linear

    def __init__(self,
                 in_features: int,
                 out_features: int,
                 bias: bool = True,
                 *,
                 nbits_weight: int = 8,
                 nbits_act: int | None = 8,
                 weight_scale_mode: str = 'per_tensor',
                 quantize_input: bool = True,
                 quantize_output: bool = False,
                 approx_w: str = 'round',
                 approx_a: str = 'round',
                 weight_fix_scale: float | torch.Tensor | None = None,
                 bias_fix_scale:   float | torch.Tensor | None = None,
                 device=None, dtype=None):
        super().__init__()
        factory_kwargs = {'device': device, 'dtype': dtype}

        self.in_features = in_features
        self.out_features = out_features
        self.weight = nn.Parameter(torch.empty(out_features, in_features, **factory_kwargs))
        self.bias = nn.Parameter(torch.zeros(out_features, **factory_kwargs)) if bias else None

        nn.init.kaiming_uniform_(self.weight, a=5 ** 0.5)
        if self.bias is not None:
            bound = 1.0 / (in_features ** 0.5)
            nn.init.uniform_(self.bias, -bound, bound)

        if weight_scale_mode != 'per_tensor':
            raise ValueError("QuantLinear only supports per-tensor weight quantization")
        self.weight_scale_mode = 'per_tensor'
        self.nbits_weight = nbits_weight
        self.nbits_act = nbits_act
        self.approx_w = approx_w
        self.approx_a = approx_a
        self.quantize_input = quantize_input and (nbits_act is not None)
        self.quantize_output = quantize_output and (nbits_act is not None)

        self.w_quant = Uniform_Quantizer_with_Collecter(
            nbits=nbits_weight, mode='value', name='linear.weight', approx=self.approx_w, verbose=False,
            fix_scale=weight_fix_scale
        )
        self.b_quant = (Uniform_Quantizer_with_Collecter(
            nbits=nbits_weight, mode='value', name='linear.bias', approx=self.approx_w, verbose=False,
            fix_scale=bias_fix_scale
        ) if bias else None)

        self.act_in_quant = (Uniform_Quantizer_with_Collecter(
            nbits=nbits_act, mode='value', name='linear.act_in', approx=self.approx_a, verbose=False
        ) if self.quantize_input else None)

        self.act_out_quant = (Uniform_Quantizer_with_Collecter(
            nbits=nbits_act, mode='value', name='linear.act_out', approx=self.approx_a, verbose=False
        ) if self.quantize_output else None)

    def _quantize_weight(self):
        return self.w_quant(self.weight)

    def _quantize_bias(self):
        if self.bias is None:
            return None
        return self.b_quant(self.bias) if self.b_quant is not None else self.bias

    def forward(self, x: torch.Tensor, *, collect: bool = False):
        if self.act_in_quant is not None:
            x = self.act_in_quant(x, collect=collect)

        Wq = self._quantize_weight()
        bq = self._quantize_bias()

        y = F.linear(x, Wq, bq)

        if self.act_out_quant is not None:
            y = self.act_out_quant(y, collect=collect)

        return y

    @torch.no_grad()
    def act_collect(self, x: torch.Tensor, *, on_input: bool = True, on_output: bool = False):
        xt = x
        if on_input and self.act_in_quant is not None:
            _ = self.act_in_quant(xt, collect=True)

        Wq = self._quantize_weight()
        bq = self._quantize_bias()
        y = F.linear(xt, Wq, bq)

        if on_output and self.act_out_quant is not None:
            _ = self.act_out_quant(y, collect=True)
        return y

    @torch.no_grad()
    def Wupdate(self):
        if self.w_quant is not None:
            self.w_quant.collector = self.weight.detach()
            self.w_quant.update()

        if self.bias is not None and self.b_quant is not None:
            self.b_quant.collector = self.bias.detach()
            self.b_quant.update()

    @torch.no_grad()
    def Qupdate(self, mode: str = 'both'):
        if mode in ['both', 'activation']:
            if self.act_in_quant is not None:
                self.act_in_quant.update()
            if self.act_out_quant is not None:
                self.act_out_quant.update()
        if mode in ['both', 'weight']:
            self.Wupdate()

    def act_update(self):
        return self.Qupdate(mode='activation')

    def reset_collector(self):
        if self.act_in_quant is not None:
            self.act_in_quant.reset_collector()
        if self.act_out_quant is not None:
            self.act_out_quant.reset_collector()

    def set_weight_fix_scale(self, s: float | torch.Tensor, *, for_bias: bool = False):
        if for_bias:
            if self.bias is None:
                return
            if self.b_quant is not None:
                self.b_quant.fix_scale = s
            return

        self.w_quant.fix_scale = s

    def clear_weight_fix_scale(self, *, for_bias: bool = False):
        if for_bias:
            if self.b_quant is not None:
                self.b_quant.fix_scale = None
            return

        self.w_quant.fix_scale = None

    def export_weight_qparams(self):
        state = {'w_scale': None, 'b_scale': None, 'nbits_weight': self.nbits_weight, 'mode': self.weight_scale_mode}
        if hasattr(self.w_quant, 'scale') and self.w_quant.scale is not None:
            state['w_scale'] = self.w_quant.scale.detach().clone()
        if self.bias is not None and self.b_quant is not None and self.b_quant.scale is not None:
            state['b_scale'] = self.b_quant.scale.detach().clone()
        return state

    def export_act_qparams(self):
        return {
            'act_in_scale': (self.act_in_quant.scale.detach().clone()
                             if (self.act_in_quant is not None and self.act_in_quant.scale is not None) else None),
            'act_out_scale': (self.act_out_quant.scale.detach().clone()
                              if (self.act_out_quant is not None and self.act_out_quant.scale is not None) else None),
            'nbits_act': self.nbits_act
        }
