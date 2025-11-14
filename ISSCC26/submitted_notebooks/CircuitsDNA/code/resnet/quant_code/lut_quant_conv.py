import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.modules.utils import _pair

from sym_quant import QuantConv2d


class Int8LUTMultiplier(nn.Module):
    """Lookup-table implementation of int8×int8 multiplication, allows approximate tables."""

    def __init__(self, table: torch.Tensor | None = None):
        super().__init__()
        if table is None:
            table = self._build_exact_table()
        if table.shape != (256, 256):
            raise ValueError("LUT shape must be 256x256")
        if table.dtype != torch.int16:
            table = table.to(torch.int16)
        self.register_buffer("table", table, persistent=False)

    @staticmethod
    def _build_exact_table() -> torch.Tensor:
        vals = torch.arange(-128, 128, dtype=torch.int16)
        return (vals.unsqueeze(1) * vals.unsqueeze(0)).to(torch.int16)

    def set_table(self, table: torch.Tensor) -> None:
        if table.shape != (256, 256):
            raise ValueError("New LUT must have shape 256x256")
        self.table = table.to(torch.int16)

    def lookup_scalar(self, a: torch.Tensor, b: torch.Tensor | int) -> torch.Tensor:
        torch._assert(a.dtype in (torch.int8, torch.int16), "input must be int8/int16")
        if isinstance(b, torch.Tensor):
            torch._assert(b.numel() == 1, "scalar multiplier must contain exactly one element")
            b_val = int(b.item())
        else:
            b_val = int(b)
        idx_b = b_val + 128
        if idx_b < 0 or idx_b >= 256:
            raise ValueError("multiplier out of int8 range")
        column = self.table[:, idx_b]
        a_idx = (a.to(torch.int16) + 128).to(torch.long)
        prod = column.gather(0, a_idx.view(-1))
        return prod.view_as(a)


class LUTQuantConv2d(QuantConv2d):
    """Quantized Conv2d that performs int8 multiplications via an LUT."""

    def __init__(
        self,
        *args,
        lut_table: torch.Tensor | None = None,
        mini_batch_size: int = 0,
        mini_channels: int = 0,
        **kwargs,
    ):

        self.mini_batch_size = int(max(mini_batch_size, 0))
        self.mini_channels = int(max(mini_channels, 0))
        super().__init__(*args, **kwargs)
        if self.nbits_weight != 8:
            raise ValueError("Only 8-bit weight quantization is supported")
        if self.nbits_act is not None and self.nbits_act != 8:
            raise ValueError("Only 8-bit activation quantization is supported")
        self.multiplier = Int8LUTMultiplier(lut_table)

    def forward(self, x: torch.Tensor, *, collect: bool = False):
        x_processed = x
        if self.act_in_quant is not None:
            x_processed = self.act_in_quant(x, collect=collect)

        bias = super()._quantize_bias()
        w_float = super()._quantize_weight()

        if collect:
            # Calibration phase: keep float forward so quantizers can collect statistics.
            y = self._forward_fallback(x_processed, w_float, bias)
        else:
            # Inference/training phase: scales must be ready.
            self._assert_scale_ready()

            x_int, act_scale = self._quantize_activation_to_int(x_processed)
            w_int, w_scales = self._quantize_weight_to_int(w_float)
            if x_int is None or w_int is None or w_scales is None:
                raise RuntimeError("LUTQuantConv2d: missing integer representations after quantization")

            # LUT provides inference values, surrogate conv supplies gradients (STE idea).
            y_lut = self._conv2d_lut(x_int, w_int, act_scale, w_scales, bias)
            y_surrogate = F.conv2d(x_processed, w_float, bias, self.stride, self.padding, self.dilation, self.groups)
            y = y_lut + (y_surrogate - y_surrogate.detach())

        if self.act_out_quant is not None:
            y = self.act_out_quant(y, collect=collect)
        return y

    def _forward_fallback(self, x_processed, w_float, bias):
        return F.conv2d(x_processed, w_float, bias, self.stride, self.padding, self.dilation, self.groups)

    def _assert_scale_ready(self) -> None:
        if not self.quantize_input or self.act_in_quant is None:
            raise RuntimeError("LUTQuantConv2d: input quantizer is disabled")
        if self.act_in_quant.scale is None:
            raise RuntimeError("LUTQuantConv2d: activation scale is not calibrated")
        if not self._weight_scale_ready():
            raise RuntimeError("LUTQuantConv2d: weight scale not ready")

    def _weight_scale_ready(self) -> bool:
        if self.weight_scale_mode == 'per_tensor':
            return self.w_quant is not None and self.w_quant.scale is not None
        if self.w_quants is None:
            return False
        return all(q.scale is not None for q in self.w_quants)

    @staticmethod
    def _q_bounds(nbits: int) -> tuple[int, int]:
        qmin = -(2 ** (nbits - 1))
        qmax = (2 ** (nbits - 1)) - 1
        return qmin, qmax

    @staticmethod
    def _ensure_scalar(scale, device) -> float:
        if scale is None:
            raise ValueError("scale must not be None")
        if torch.is_tensor(scale):
            return float(scale.detach().to(device=device).item())
        return float(scale)

    def _quantize_activation_to_int(self, x_q: torch.Tensor): # The pseudo-quantized value remains as a float. It is generated into an accurate int8 code value through division by "scale" and rounding.
        if self.act_in_quant is None or self.act_in_quant.scale is None:
            return None, None
        scale_val = self._ensure_scalar(self.act_in_quant.scale, x_q.device)
        qmin, qmax = self._q_bounds(self.nbits_act)
        x_int = torch.round(x_q / scale_val).clamp(qmin, qmax).to(torch.int16)
        return x_int, scale_val

    def _quantize_weight_to_int(self, w_float: torch.Tensor | None = None):
        qmin, qmax = self._q_bounds(self.nbits_weight)
        if self.weight_scale_mode == 'per_tensor':
            if self.w_quant is None or self.w_quant.scale is None:
                return None, None
            target = self.weight if w_float is None else w_float
            scale_val = self._ensure_scalar(self.w_quant.scale, target.device)
            # In the per-tensor case, all channels share the same scale.
            w_int = torch.round(target / scale_val).clamp(qmin, qmax).to(torch.int16)
            return w_int, torch.tensor([scale_val], device=target.device, dtype=torch.float32)
        if self.w_quants is None:
            return None, None
        weight_src = self.weight if w_float is None else w_float
        w_int_list = []
        scales = []
        for idx, q in enumerate(self.w_quants):
            if q.scale is None:
                return None, None
            s = self._ensure_scalar(q.scale, weight_src.device)
            scales.append(s)
            w_int = torch.round(weight_src[idx] / s).clamp(qmin, qmax).to(torch.int16)
            w_int_list.append(w_int)
        stacked = torch.stack(w_int_list, dim=0)
        return stacked, torch.tensor(scales, device=weight_src.device, dtype=torch.float32)

    def _conv2d_lut(
        self,
        x_int: torch.Tensor,
        w_int: torch.Tensor,
        act_scale: float,
        weight_scales: torch.Tensor,
        bias: torch.Tensor | None,
    ) -> torch.Tensor:
        stride = _pair(self.stride)
        padding = _pair(self.padding)
        dilation = _pair(self.dilation)
        kH, kW = w_int.shape[2], w_int.shape[3]

        # Unfold + reshape to expose each sliding window for vectorized LUT lookup.
        x_cols = F.unfold(x_int.to(torch.float32), (kH, kW), dilation=dilation, padding=padding, stride=stride)
        x_cols = x_cols.to(torch.int16)
        N, _, L = x_cols.shape
        C_out = w_int.shape[0]
        groups = self.groups
        C_in = x_int.shape[1]
        cin_per_group = C_in // groups
        cout_per_group = C_out // groups
        kernel_elems = cin_per_group * kH * kW
        x_cols = x_cols.view(N, groups, kernel_elems, L)
        w_flat = w_int.view(groups, cout_per_group, kernel_elems)

        # Pre-compute combined scales for input/weight products.
        scales = weight_scales.to(dtype=torch.float32, device=x_int.device)
        if scales.numel() == 1:
            scales = scales.expand(C_out)
        else:
            torch._assert(scales.numel() == C_out, "weight scale shape mismatch")
        scales = scales * float(act_scale)

        table = self.multiplier.table.to(device=x_int.device, dtype=torch.int16)
        x_idx = (x_cols.to(torch.int32) + 128).clamp_(0, 255).to(torch.long)
        w_idx = (w_flat.to(torch.int32) + 128).clamp_(0, 255).to(torch.long)

        output = torch.zeros(N, C_out, L, dtype=torch.float32, device=x_int.device)
        mini_batch = self.mini_batch_size or N
        mini_channel = self.mini_channels or cout_per_group

        # Two-level chunking (batch -> group -> channel) controls peak memory usage.
        for b_start in range(0, N, mini_batch):
            b_end = min(b_start + mini_batch, N)
            x_batch = x_idx[b_start:b_end]  # [B, groups, K, L]
            for g_idx in range(groups):
                x_block = x_batch[:, g_idx]  # [B, K, L]
                w_group = w_idx[g_idx]       # [cout_per_group, K]
                channel_base = g_idx * cout_per_group
                for c_start in range(0, cout_per_group, mini_channel):
                    c_end = min(c_start + mini_channel, cout_per_group)
                    w_chunk = w_group[c_start:c_end]  # [Cchunk, K]

                    # Build table indices via broadcasting, avoiding Python loops.
                    x_sel = x_block.unsqueeze(1)  # [B,1,K,L]
                    x_sel = x_sel.expand(-1, w_chunk.size(0), -1, -1)
                    w_sel = w_chunk.unsqueeze(0).unsqueeze(-1)  # [1,Cchunk,K,1]
                    w_sel = w_sel.expand(b_end - b_start, -1, -1, L)

                    prod = table[x_sel, w_sel].to(torch.int32)  # [B, Cchunk, K, L]
                    acc = prod.sum(dim=2)  # Reduce the kernel dimension → [B, Cchunk, L]

                    scale_chunk = scales[channel_base + c_start: channel_base + c_end]
                    output[b_start:b_end, channel_base + c_start: channel_base + c_end] = (
                        acc.to(torch.float32) * scale_chunk.view(1, -1, 1)
                    )

        if bias is not None:
            output += bias.view(1, -1, 1).to(output.dtype)

        H_out = int((x_int.shape[2] + 2 * padding[0] - dilation[0] * (kH - 1) - 1) / stride[0] + 1)
        W_out = int((x_int.shape[3] + 2 * padding[1] - dilation[1] * (kW - 1) - 1) / stride[1] + 1)
        return output.view(x_int.shape[0], C_out, H_out, W_out)

