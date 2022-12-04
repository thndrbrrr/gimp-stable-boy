<a name="readme-top"></a>

<div>
<h1 align="center">Stable Boy</h1>
  <p align="center">
    A GIMP plugin for AUTOMATIC1111's Stable Diffusion WebUI
  </p>
</div>

<!-- ABOUT THE PROJECT -->
## About

[AUTOMATIC1111's Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) is one of the most powerful tools in the generative AI space. Stable Boy puts that power into GIMP 2.10 by calling into A1111 WebUI's API.

Here's a short demo video of what Stable Boy can do at the moment:

[![A short demo](./public/images/demo-video-screenshot.png)](https://youtu.be/YMVog30OcTI)


<p align="right">(<a href="#readme-top">back to top</a>)</p>


## Installation

1. Clone the repo:
   ```sh
   git clone https://github.com/tgiesselmann/gimp-stable-boy.git
   ```
2. Start GIMP
3. Add the absolute path to _sub-folder_ (!) `src/gimp-stable-boy` to GIMP's plugin search path:
   ```
   /home/...and-so-on.../gimp-stable-boy/src/gimp-stable-boy     # MacOS, Linux
   C:/Users/...and-so-on.../gimp-stable-boy/src/gimp-stable-boy  # Windows
   ```
   ![GIMP Preferences](public/images/gimp-prefs-plugin-path.png)
4. Restart GIMP.
5. Create a new file with a reasonable size, like `512x512`.
6. Stable Boy can be found in the `Stable Boy` menu, with the following options:
   1. Text to Image
   2. Image to Image
   3. Inpainting
   4. Extras (for upscaling)
7. Start A1111 WebUI with argument `--api`. It doesn't matter whether it's running on your local machine or somewhere in the cloud.
8. Copy-paste A1111 WebUI's URL (something like `https://abcdef123.gradio.com`) into the `API URL` field. (For the time being you'll have to do that once for every generation option.)


<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- USAGE EXAMPLES -->
## Usage

For inpainting to work you will need to add a layer with name "`Inpainting Mask`" to the image (see video). Loading an inpainting model in A1111's WebUI would also be a good idea.

**Note:** Stable Boy doesn't have an option to choose the model. You'll have to do that in WebUI.

(More documentation to come.)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ROADMAP -->
## Roadmap

- [ ] Outpainting
- [ ] Rectangular selections as image sources for each mode
- [ ] Better GUI
- [ ] Support for more options
- [ ] Better documentation

See the [open issues](https://github.com/tgiesselmann/gimp-stable-boy/issues) for known issues.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**. If you have a suggestion that would make this better, please fork the repo and create a pull request. Thank you!

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Adding some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a pull request

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- LICENSE -->
## License

Distributed under the GNU General Public License v3.0. See file [`COPYING`](COPYING) for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Torben: tsgiesselmann@gmail.com

Stable Boy: [https://github.com/tgiesselmann/gimp-stable-boy](https://github.com/tgiesselmann/gimp-stable-boy)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

In the end, everyone stands on the shoulders of giants.

* [Stable Diffusion](https://github.com/CompVis/stable-diffusion)
* [AUTOMATIC1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
* [GIMP](https://www.gimp.org/)
* [blueturtleai's gimp-stable-diffusion](https://github.com/blueturtleai/gimp-stable-diffusion)
* [Stack Overflow](https://stackoverflow.com/)
* [Othneil Drew](https://github.com/othneildrew)

<p align="right">(<a href="#readme-top">back to top</a>)</p>
