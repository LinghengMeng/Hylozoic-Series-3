Hylozoic Series 3 Interactive Control System
======================

 Combining techniques in architecture, the arts, electronics, and software, the Living Architecture System Group (LASG) develops interactive art sculptures that engage occupants in an immersive environment. The overarching goal of this research is to develop architectural systems that possess life-like qualities. In the Hylozoic Series kinetic sculptures built by [Philip Beesley Architect Inc.](http://philipbeesleyarchitect.com/), the designers use a network of microcontrollers to control and sample a sizable number of actuators and sensors. Each node in the network can perform a simple set of interactive behaviours. Though complexity may emerge in previous systems through superposition of a set of simple and prescripted behaviours, the responses of the systems to occupants remain rather robotic and ultimately dictated by the will of the designers. 

To enable the sculpture to automatically generate interactive behaviours and
adapt to changes, Curiosity-Based Learning Algorithm (CBLA), a reinforcement learning algorithm which selects actions that lead to maximum potential knowledge gains, is introduced.

To realize the CBLA system on a physical interactive art sculpture, an overhaul of the previous series’ interactive control hardware was necessary. CBLA requires the system to be able to sense the consequences of its own actions and its surrounding at a much higher resolution and frequency than previously implemented behaviour algorithms. This translates to the need to interface and collect samples from a substantially larger number of sensors. 

The **Hylozoic Series 3 Interactive Control System** consists of a new set of hardware and control system software was developed. It enables the control and sampling of hundreds of devices on a centralized computer through USB connections. Moving the computation from an embedded platform simpliﬁes the implementation of the CBLA system, which is a computationally intensive and complex
program. In addition, the large amount of data generated by the system can now be recorded without sacriﬁcing response time nor resolution.

## Contents




## Contributors
* Matthew Tsz Kiu Chan (University of Waterloo)
* Mohammedreza Memarian (University of Waterloo)
* Matt Borland (Philip Beesley Architect Inc.)
* David Kadish (Philip Beesley Architect Inc.)
