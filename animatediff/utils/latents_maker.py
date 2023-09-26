# -- coding: utf-8 --
# @Time : 2023/9/26
# @Author : ykk648
# @Project : https://github.com/ykk648/AnimateDiff
import PIL
from animatediff.utils.util import preprocess_image
import torch
# from cv2box import CVImage
# from einops import rearrange, repeat

def prepare_latents(self, init_image, batch_size, num_channels_latents, video_length, height, width, dtype, device,
                    generator, timestep=None, latents=None, **kwargs):
    shape = (
        batch_size, num_channels_latents, video_length, height // self.vae_scale_factor,
        width // self.vae_scale_factor)

    if init_image is not None:
        image = PIL.Image.open(init_image)
        image = preprocess_image(image)
        if not isinstance(image, (torch.Tensor, PIL.Image.Image, list)):
            raise ValueError(
                f"`image` has to be of type `torch.Tensor`, `PIL.Image.Image` or list but is {type(image)}"
            )
        image = image.to(device=device, dtype=dtype)
        if isinstance(generator, list):
            init_latents = [
                self.vae.encode(image[i: i + 1]).latent_dist.sample(generator[i]) for i in range(batch_size)
            ]
            init_latents = torch.cat(init_latents, dim=0)
        else:
            init_latents = self.vae.encode(image.to(device, dtype=self.vae.dtype)).latent_dist.sample(generator)
    else:
        init_latents = None

    if isinstance(generator, list) and len(generator) != batch_size:
        raise ValueError(
            f"You have passed a list of generators of length {len(generator)}, but requested an effective batch"
            f" size of {batch_size}. Make sure the batch size matches the length of the generators."
        )
    if latents is None:
        rand_device = "cpu" if device.type == "mps" else device

        if isinstance(generator, list):
            shape = shape
            # shape = (1,) + shape[1:]
            # ignore init latents for batch model
            latents = [
                torch.randn(shape, generator=generator[i], device=rand_device, dtype=dtype)
                for i in range(batch_size)
            ]
            latents = torch.cat(latents, dim=0).to(device)
        else:
            latents = torch.randn(shape, generator=generator, device=rand_device, dtype=dtype).to(device)

            if timestep:

                # ref diffusers img2img
                init_latents = init_latents * 0.18215
                init_latents = init_latents.unsqueeze(2).repeat(1, 1, video_length, 1, 1)

                # from cv2box import get_path_by_ext
                # init_latents_gifs = []
                # for image_p in get_path_by_ext(./samples/AstronautMars_v2_motionlora-2023-09-26T02-04-19/test', sorted_by_stem=True):
                #     image = CVImage(str(image_p)).pillow() # pil is stupid
                #     image = preprocess_image(image)
                #     image = image.to(device=device, dtype=dtype)
                #     init_latent_gif = self.vae.encode(image.to(device, dtype=self.vae.dtype)).latent_dist.sample(generator)
                #     init_latent_gif = init_latent_gif * 0.18215
                #     init_latents_gifs.append(init_latent_gif.unsqueeze(0))
                # init_latents_gifs = torch.concatenate(init_latents_gifs) # 16 1 4 64 64
                # # init_latents_gif.rearrange((1,2,0,3,4))
                # init_latents_gifs = rearrange(init_latents_gifs, "f b c h w -> b c f h w")

                # noise_patten = [1, 1, 1, 1, 0.6, 0.6, 0.6, 0.6, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3]
                # for i in range(video_length):
                #     init_latents[:, :, i, :, :] = init_latents[:, :, i, :, :]*noise_patten[i]
                # equal to "latents[:,:, i,:,:] = init_latents * 0.3259 + latents[:,:, i,:,:] * 0.9454"
                latents = self.scheduler.add_noise(init_latents, latents, timestep)

            # ref https://github.com/kabachuha/sd-webui-text2video
            # from types import SimpleNamespace
            # from ..utils.key_frames import T2VAnimKeys
            # keys = T2VAnimKeys(
            #     SimpleNamespace(**{'max_frames': video_length, 'inpainting_weights': "0:(0), \"max_i_f/4\":(1), \"3*max_i_f/4\":(1), \"max_i_f-1\":(0)"}),
            #     seed, video_length)
            # mask_weights = [keys.inpainting_weights_series[frame_idx] for frame_idx in range(video_length)]
            # # [0.0, 0.3333333333333333, 0.6666666666666666, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.6666666666666667, 0.33333333333333337, 0.0, 0.0]

            # old noise policy ref talesofai
            # if init_latents is not None:
            #
            #     # init_alpha = [0.1, 0.09, 0.08, 0.07, 0.06, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05,
            #     #               0.05, 0.05]
            #
            #     init_alpha = kwargs['init_alpha']
            #     init_alpha_copy = kwargs['init_alpha']
            #     truncate_alpha = kwargs['truncate_alpha']  # hyper-parameters
            #     alpha_step = kwargs['alpha_step']  # hyper-parameters
            #     alpha_list = []
            #     for i in range(video_length):
            #         # # ref https://github.com/talesofai/AnimateDiff
            #         # init_alpha = (video_length - float(i)) / video_length / 30
            #         # latents[:, :, i, :, :] = init_latents * init_alpha + latents[:, :, i, :, :] * (1 - init_alpha)
            #
            #         # truncate the alpha value
            #         if init_alpha != truncate_alpha and init_alpha != 0:
            #             init_alpha = round(init_alpha_copy - i * alpha_step, 2)  # decimal
            #         assert init_alpha >= 0
            #         alpha_list.append(init_alpha)
            #         latents[:, :, i, :, :] = init_latents * init_alpha + latents[:, :, i, :, :] * (1 - init_alpha)
            #     print(alpha_list)
    else:
        if latents.shape != shape:
            raise ValueError(f"Unexpected latents shape, got {latents.shape}, expected {shape}")
        latents = latents.to(device)

    # scale the initial noise by the standard deviation required by the scheduler
    if init_latents is None:
        # print(self.scheduler.init_noise_sigma) # 1.0
        latents = latents * self.scheduler.init_noise_sigma
    return latents