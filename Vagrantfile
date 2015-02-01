VAGRANTFILE_API_VERSION = "2"

$install_script = <<SCRIPT
export DEBIAN_FRONTEND="noninteractive"

apt-get install -y python3
apt-get install -y python3-pip

SCRIPT

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
 
  config.vm.provision :shell, :inline => $install_script
  config.vm.box = "ubuntu/trusty64"
  config.ssh.forward_agent = true
  config.vm.network "forwarded_port", guest: 5432, host: 5432
  config.vm.network "forwarded_port", guest: 5433, host: 5433
  config.vm.network "forwarded_port", guest: 5434, host: 5434
  config.vm.provision "docker"

end
