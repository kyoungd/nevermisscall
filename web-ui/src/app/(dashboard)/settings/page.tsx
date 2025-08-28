'use client'

import React from 'react'
import { useAuthStore } from '@/store/auth'
import { useUIStore } from '@/store/ui'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { 
  Settings,
  User,
  Bell,
  Palette,
  Shield,
  Phone,
  Save,
  Upload
} from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { getInitials } from '@/lib/utils'
import { useTheme } from 'next-themes'

export default function SettingsPage() {
  const { user, updateUser } = useAuthStore()
  const { setBreadcrumbs, setCurrentPage, showSuccessToast, showErrorToast } = useUIStore()
  const { theme, setTheme } = useTheme()
  
  const [profileData, setProfileData] = React.useState({
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    email: user?.email || '',
    phone: user?.phone || '',
    timezone: user?.timezone || 'America/New_York'
  })

  const [preferences, setPreferences] = React.useState({
    theme: theme || 'system',
    emailNotifications: user?.preferences.notifications.email ?? true,
    pushNotifications: user?.preferences.notifications.push ?? true,
    desktopNotifications: user?.preferences.notifications.desktop ?? true,
    soundsEnabled: user?.preferences.notifications.sounds ?? true,
    autoRefresh: user?.preferences.dashboard.autoRefresh ?? true,
    refreshInterval: user?.preferences.dashboard.refreshInterval ?? 30000
  })

  React.useEffect(() => {
    setCurrentPage('Settings')
    setBreadcrumbs([{ label: 'Settings' }])
  }, [setCurrentPage, setBreadcrumbs])

  const handleProfileSave = async () => {
    try {
      // In a real implementation, this would call the API
      updateUser(profileData)
      showSuccessToast('Profile updated successfully')
    } catch (error: any) {
      showErrorToast(error.message || 'Failed to update profile')
    }
  }

  const handlePreferencesSave = async () => {
    try {
      // Update theme
      setTheme(preferences.theme)
      
      // In a real implementation, this would call the API to update user preferences
      updateUser({
        preferences: {
          ...user?.preferences,
          theme: preferences.theme as any,
          notifications: {
            email: preferences.emailNotifications,
            push: preferences.pushNotifications,
            desktop: preferences.desktopNotifications,
            sounds: preferences.soundsEnabled
          },
          dashboard: {
            ...user?.preferences.dashboard,
            autoRefresh: preferences.autoRefresh,
            refreshInterval: preferences.refreshInterval
          }
        }
      })
      
      showSuccessToast('Preferences updated successfully')
    } catch (error: any) {
      showErrorToast(error.message || 'Failed to update preferences')
    }
  }

  const handleAvatarUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      // In a real implementation, this would upload the file to a server
      console.log('Upload avatar:', file)
      showSuccessToast('Avatar upload would be implemented here')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">
            Manage your account settings and preferences
          </p>
        </div>
      </div>

      {/* Settings Tabs */}
      <Tabs defaultValue="profile" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="profile" className="flex items-center gap-2">
            <User className="h-4 w-4" />
            Profile
          </TabsTrigger>
          <TabsTrigger value="notifications" className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Notifications
          </TabsTrigger>
          <TabsTrigger value="appearance" className="flex items-center gap-2">
            <Palette className="h-4 w-4" />
            Appearance
          </TabsTrigger>
          <TabsTrigger value="security" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Security
          </TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Profile Information
              </CardTitle>
              <CardDescription>
                Update your personal information and contact details
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Avatar */}
              <div className="flex items-center space-x-4">
                <Avatar className="h-20 w-20">
                  <AvatarImage src={user?.avatar} />
                  <AvatarFallback className="text-lg bg-primary text-primary-foreground">
                    {user ? getInitials(`${user.firstName} ${user.lastName}`) : 'U'}
                  </AvatarFallback>
                </Avatar>
                <div className="space-y-2">
                  <Label htmlFor="avatar-upload" className="cursor-pointer">
                    <Button variant="outline" className="h-auto">
                      <Upload className="mr-2 h-4 w-4" />
                      Change Avatar
                    </Button>
                  </Label>
                  <input
                    id="avatar-upload"
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleAvatarUpload}
                  />
                  <p className="text-xs text-muted-foreground">
                    JPG, PNG or GIF. Max size 5MB.
                  </p>
                </div>
              </div>

              {/* Personal Information */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name</Label>
                  <Input
                    id="firstName"
                    value={profileData.firstName}
                    onChange={(e) => setProfileData({ ...profileData, firstName: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name</Label>
                  <Input
                    id="lastName"
                    value={profileData.lastName}
                    onChange={(e) => setProfileData({ ...profileData, lastName: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  value={profileData.email}
                  onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">Phone Number</Label>
                <Input
                  id="phone"
                  type="tel"
                  value={profileData.phone}
                  onChange={(e) => setProfileData({ ...profileData, phone: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="timezone">Timezone</Label>
                <Select value={profileData.timezone} onValueChange={(value) => setProfileData({ ...profileData, timezone: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="America/New_York">Eastern Time</SelectItem>
                    <SelectItem value="America/Chicago">Central Time</SelectItem>
                    <SelectItem value="America/Denver">Mountain Time</SelectItem>
                    <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                    <SelectItem value="UTC">UTC</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button onClick={handleProfileSave} className="w-full sm:w-auto">
                <Save className="mr-2 h-4 w-4" />
                Save Profile
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Notification Preferences
              </CardTitle>
              <CardDescription>
                Choose how you want to be notified about events
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Email Notifications</Label>
                    <p className="text-sm text-muted-foreground">
                      Receive notifications via email
                    </p>
                  </div>
                  <Switch
                    checked={preferences.emailNotifications}
                    onCheckedChange={(checked) => setPreferences({ ...preferences, emailNotifications: checked })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Push Notifications</Label>
                    <p className="text-sm text-muted-foreground">
                      Receive push notifications on your devices
                    </p>
                  </div>
                  <Switch
                    checked={preferences.pushNotifications}
                    onCheckedChange={(checked) => setPreferences({ ...preferences, pushNotifications: checked })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Desktop Notifications</Label>
                    <p className="text-sm text-muted-foreground">
                      Show desktop notifications in your browser
                    </p>
                  </div>
                  <Switch
                    checked={preferences.desktopNotifications}
                    onCheckedChange={(checked) => setPreferences({ ...preferences, desktopNotifications: checked })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Sound Notifications</Label>
                    <p className="text-sm text-muted-foreground">
                      Play sounds for notifications
                    </p>
                  </div>
                  <Switch
                    checked={preferences.soundsEnabled}
                    onCheckedChange={(checked) => setPreferences({ ...preferences, soundsEnabled: checked })}
                  />
                </div>
              </div>

              <Button onClick={handlePreferencesSave} className="w-full sm:w-auto">
                <Save className="mr-2 h-4 w-4" />
                Save Preferences
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Appearance Tab */}
        <TabsContent value="appearance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="h-5 w-5" />
                Appearance Settings
              </CardTitle>
              <CardDescription>
                Customize the look and feel of your dashboard
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Theme</Label>
                  <Select value={preferences.theme} onValueChange={(value) => setPreferences({ ...preferences, theme: value })}>
                    <SelectTrigger className="w-[200px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="light">Light</SelectItem>
                      <SelectItem value="dark">Dark</SelectItem>
                      <SelectItem value="system">System</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-sm text-muted-foreground">
                    Choose your preferred theme or use system setting
                  </p>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Auto Refresh</Label>
                    <p className="text-sm text-muted-foreground">
                      Automatically refresh dashboard data
                    </p>
                  </div>
                  <Switch
                    checked={preferences.autoRefresh}
                    onCheckedChange={(checked) => setPreferences({ ...preferences, autoRefresh: checked })}
                  />
                </div>

                {preferences.autoRefresh && (
                  <div className="space-y-2">
                    <Label>Refresh Interval (seconds)</Label>
                    <Select 
                      value={preferences.refreshInterval.toString()} 
                      onValueChange={(value) => setPreferences({ ...preferences, refreshInterval: parseInt(value) })}
                    >
                      <SelectTrigger className="w-[200px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="15000">15 seconds</SelectItem>
                        <SelectItem value="30000">30 seconds</SelectItem>
                        <SelectItem value="60000">1 minute</SelectItem>
                        <SelectItem value="300000">5 minutes</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>

              <Button onClick={handlePreferencesSave} className="w-full sm:w-auto">
                <Save className="mr-2 h-4 w-4" />
                Save Appearance
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Security Settings
              </CardTitle>
              <CardDescription>
                Manage your account security and privacy
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-medium">Change Password</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Update your password to keep your account secure
                  </p>
                  <Button variant="outline">
                    Change Password
                  </Button>
                </div>

                <div>
                  <h3 className="text-lg font-medium">Two-Factor Authentication</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Add an extra layer of security to your account
                  </p>
                  <Button variant="outline">
                    Enable 2FA
                  </Button>
                </div>

                <div>
                  <h3 className="text-lg font-medium">Active Sessions</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Manage devices that are signed into your account
                  </p>
                  <Button variant="outline">
                    View Sessions
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}